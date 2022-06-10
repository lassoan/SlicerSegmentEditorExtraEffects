import os
import vtk, qt, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses markup fiducials to segment the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Engrave'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

    self.logic = EngraveLogic(scriptedEffect)

    # Effect-specific members
    self.segmentMarkupNode = None
    self.segmentMarkupNodeObservers = []
    self.segmentEditorNode = None
    self.segmentEditorNodeObserver = None
    self.segmentModel = None
    self.observedSegmentation = None
    self.segmentObserver = None
    self.buttonToModeTypeMap = {}

  def clone(self):
    # It should not be necessary to modify this method
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\','/'))
    return clonedEffect

  def icon(self):
    # It should not be necessary to modify this method
    iconPath = os.path.join(os.path.dirname(__file__), 'SegmentEditorEffect.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return """<html>Engrave or emboss text on a segment's surface</html>"""

  def setupOptionsFrame(self):
    self.modeRadioButtons = []

    # Text line edit
    self.textLineEdit = qt.QLineEdit()
    self.textLineEdit.setToolTip("Text to be added")
    self.textLineEdit.text = "Text"
    self.textLineEditLabel = self.scriptedEffect.addLabeledOptionsWidget("Text:", self.textLineEdit)

    # Fiducial Placement widget
    self.markupsPlacementToggle = slicer.qSlicerMarkupsPlaceWidget()
    self.markupsPlacementToggle.setMRMLScene(slicer.mrmlScene)
    self.markupsPlacementToggle.placeMultipleMarkups = self.markupsPlacementToggle.ForcePlaceSingleMarkup
    self.markupsPlacementToggle.buttonsVisible = False
    self.markupsPlacementToggle.show()
    self.markupsPlacementToggle.placeButton().show()
    self.markupsPlacementToggle.deleteButton().show()

    # Edit surface button
    self.editButton = qt.QPushButton("Edit")
    self.editButton.objectName = self.__class__.__name__ + 'Edit'
    self.editButton.setToolTip("Edit the previously placed plane.")

    markupsActionLayout = qt.QHBoxLayout()
    markupsActionLayout.addWidget(self.markupsPlacementToggle)
    markupsActionLayout.addWidget(self.editButton)
    self.scriptedEffect.addLabeledOptionsWidget("Placement: ", markupsActionLayout)

    # Resize button
    self.interactionResizeButton = qt.QPushButton("Resize")
    self.interactionResizeButton.objectName = self.__class__.__name__ + 'Resize'
    self.interactionResizeButton.checkable = True
    self.interactionResizeButton.setToolTip("Enable/disable resize of the text plane.")

    # Move button
    self.interactionMoveButton = qt.QPushButton("Move")
    self.interactionMoveButton.objectName = self.__class__.__name__ + 'Move'
    self.interactionMoveButton.checkable = True
    self.interactionMoveButton.setToolTip("Enable/disable translation and rotation of the text plane.")

    interactionLayout = qt.QHBoxLayout()
    interactionLayout.addWidget(self.interactionResizeButton)
    interactionLayout.addWidget(self.interactionMoveButton)
    self.scriptedEffect.addLabeledOptionsWidget("Interaction: ", interactionLayout)

    # Text depth slider
    self.textDepthSlider = ctk.ctkSliderWidget()
    self.textDepthSlider.setToolTip("Thickness of the generated text.")
    self.textDepthSlider.minimum = 0.1
    self.textDepthSlider.maximum = 20.0
    self.textDepthSlider.value = 5
    self.textDepthSlider.singleStep = 0.1
    self.textDepthSlider.pageStep = 1.0
    self.textDepthLabel = self.scriptedEffect.addLabeledOptionsWidget("Depth:", self.textDepthSlider)

    # Mode buttons
    self.engraveButton = qt.QRadioButton("Engrave")
    self.modeRadioButtons.append(self.engraveButton)
    self.buttonToModeTypeMap[self.engraveButton] = "ENGRAVE"

    self.embossButton = qt.QRadioButton("Emboss")
    self.modeRadioButtons.append(self.embossButton)
    self.buttonToModeTypeMap[self.embossButton] = "EMBOSS"

    # Mode buttons layout
    modeLayout = qt.QVBoxLayout()
    modeLayout.addWidget(self.engraveButton)
    modeLayout.addWidget(self.embossButton)

    self.scriptedEffect.addLabeledOptionsWidget("Mode:", modeLayout)

    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Generate tube from markup fiducials.")
    self.scriptedEffect.addOptionsWidget(self.applyButton)

    # Cancel button
    self.cancelButton = qt.QPushButton("Cancel")
    self.cancelButton.objectName = self.__class__.__name__ + 'Cancel'
    self.cancelButton.setToolTip("Clear fiducials and remove from scene.")

    # Finish action buttons
    finishAction = qt.QHBoxLayout()
    finishAction.addWidget(self.cancelButton)
    finishAction.addWidget(self.applyButton)
    self.scriptedEffect.addOptionsWidget(finishAction)

    # Connections
    for button in self.modeRadioButtons:
      button.connect('toggled(bool)',
      lambda toggle, widget=self.buttonToModeTypeMap[button]: self.onModeSelectionChanged(widget, toggle))
    self.applyButton.connect('clicked()', self.onApply)
    self.cancelButton.connect('clicked()', self.onCancel)
    self.editButton.connect('clicked()', self.onEdit)
    self.markupsPlacementToggle.placeButton().clicked.connect(self.onmarkupsPlacementToggleChanged)
    self.interactionResizeButton.connect('toggled(bool)', self.onInteractionResizeEnabled)
    self.interactionMoveButton.connect('toggled(bool)', self.onInteractionMoveEnabled)
    self.textLineEdit.connect("textEdited(QString)", self.onTextChanged)
    self.textDepthSlider.connect('valueChanged(double)', self.onTextDepthChanged)

  def activate(self):
    self.scriptedEffect.showEffectCursorInSliceView = False
    # Create model node prior to markup node to display markups over the model
    if not self.segmentModel:
      self.createNewModelNode()
    # Create empty markup fiducial node
    if not self.segmentMarkupNode:
      self.createNewMarkupNode()
      self.markupsPlacementToggle.setCurrentNode(self.segmentMarkupNode)
      self.setAndObserveSegmentMarkupNode(self.segmentMarkupNode)
      self.markupsPlacementToggle.setPlaceModeEnabled(False)
    self.setAndObserveSegmentEditorNode(self.scriptedEffect.parameterSetNode())
    self.observeSegmentation(True)
    self.updateGUIFromMRML()

  def deactivate(self):
    self.reset()
    self.observeSegmentation(False)
    self.setAndObserveSegmentEditorNode(None)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("Text", "Text")
    self.scriptedEffect.setParameterDefault("Mode", "ENGRAVE")
    self.scriptedEffect.setParameterDefault("TextDepth", 5.0)

  def updateGUIFromMRML(self):
    if slicer.mrmlScene.IsClosing():
      return

    if self.segmentMarkupNode:
      self.cancelButton.setEnabled(self.getNumberOfDefinedControlPoints() != 0)
      self.applyButton.setEnabled(self.segmentMarkupNode.GetIsPlaneValid())
      self.interactionResizeButton.setEnabled(self.segmentMarkupNode.GetIsPlaneValid())
      self.interactionMoveButton.setEnabled(self.segmentMarkupNode.GetIsPlaneValid())
      segmentMarkupDisplayNode = self.segmentMarkupNode.GetDisplayNode()
      if segmentMarkupDisplayNode:
        wasBlocked = self.interactionResizeButton.blockSignals(True)
        self.interactionResizeButton.checked = segmentMarkupDisplayNode.GetHandlesInteractive() and segmentMarkupDisplayNode.GetScaleHandleVisibility()
        self.interactionResizeButton.blockSignals(wasBlocked)
        wasBlocked = self.interactionMoveButton.blockSignals(True)
        self.interactionMoveButton.checked = segmentMarkupDisplayNode.GetHandlesInteractive() and segmentMarkupDisplayNode.GetTranslationHandleVisibility()
        self.interactionMoveButton.blockSignals(wasBlocked)

      # Prevent placing additional planes
      self.markupsPlacementToggle.placeButton().setVisible(not self.segmentMarkupNode.GetIsPlaneValid())
      segmentMarkupDisplayNode = self.segmentMarkupNode.GetDisplayNode()

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    if segmentID and segmentationNode:
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      if segment:
        self.editButton.setVisible(segment.HasTag("EngraveEffectPlaneParameters"))

    modeName = self.scriptedEffect.parameter("Mode")
    modeButton = list(self.buttonToModeTypeMap.keys())[list(self.buttonToModeTypeMap.values()).index(modeName)]
    modeButton.setChecked(True)

    if self.textLineEdit.text != self.scriptedEffect.parameter("Text"):
      wasBlocked = self.textLineEdit.blockSignals(True)
      self.textLineEdit.text = self.scriptedEffect.parameter("Text")
      self.textLineEdit.blockSignals(wasBlocked)

    wasBlocked = self.textDepthSlider.blockSignals(True)
    self.textDepthSlider.value = self.scriptedEffect.doubleParameter("TextDepth")
    self.textDepthSlider.blockSignals(wasBlocked)

  #
  # Effect specific methods (the above ones are the API methods to override)
  #

  def onModeSelectionChanged(self, modeName, toggle):
    if not toggle:
      return
    self.scriptedEffect.setParameter("Mode", modeName)
    self.updateModelFromSegmentMarkupNode()

  def onmarkupsPlacementToggleChanged(self):
    if self.markupsPlacementToggle.placeButton().isChecked():
      # Create empty model node
      if self.segmentModel is None:
        self.createNewModelNode()

      # Create empty markup fiducial node
      if self.segmentMarkupNode is None:
        self.createNewMarkupNode()
        self.markupsPlacementToggle.setCurrentNode(self.segmentMarkupNode)

  def onTextChanged(self, text):
    self.scriptedEffect.setParameter("Text", text)
    self.updateModelFromSegmentMarkupNode()

  def onTextDepthChanged(self, depth):
    self.scriptedEffect.setParameter("TextDepth", depth)
    self.updateModelFromSegmentMarkupNode()

  def onSegmentModified(self, caller, event):
    if not self.editButton.isEnabled() and self.segmentMarkupNode.GetNumberOfControlPoints() != 0:
      self.reset()
      # Create model node prior to markup node for display order
      self.createNewModelNode()
      self.createNewMarkupNode()
      self.markupsPlacementToggle.setCurrentNode(self.segmentMarkupNode)
    else:
      self.updateGUIFromMRML()

  def onCancel(self):
    self.reset()
    # Create model node prior to markup node for display order
    self.createNewModelNode()
    self.createNewMarkupNode()
    self.markupsPlacementToggle.setCurrentNode(self.segmentMarkupNode)

  def onEdit(self):
    # Create empty model node
    if self.segmentModel is None:
      self.createNewModelNode()

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)

    fPosStr = vtk.mutable("")
    segment.GetTag("EngraveEffectPlaneParameters", fPosStr)
    # convert from space-separated list of numbers to 1D array
    import numpy
    planeParameters = numpy.fromstring(str(fPosStr), sep=' ')

    if len(planeParameters) > 0:
      self.segmentMarkupNode.SetOriginWorld(planeParameters[0:3])
      self.segmentMarkupNode.SetAxesWorld(planeParameters[3:6], planeParameters[6:9], planeParameters[9:12])
      self.segmentMarkupNode.SetPlaneBounds(planeParameters[12:16])

    self.editButton.setEnabled(False)
    self.updateModelFromSegmentMarkupNode()

  def reset(self):
    if self.markupsPlacementToggle.placeModeEnabled:
      self.markupsPlacementToggle.setPlaceModeEnabled(False)

    if not self.editButton.isEnabled():
      self.editButton.setEnabled(True)

    if self.segmentModel:
      if self.segmentModel.GetScene():
        slicer.mrmlScene.RemoveNode(self.segmentModel)
      self.segmentModel = None

    if self.segmentMarkupNode:
      if self.segmentMarkupNode.GetScene():
        slicer.mrmlScene.RemoveNode(self.segmentMarkupNode)
      self.setAndObserveSegmentMarkupNode(None)

  def onApply(self):
    if not self.segmentMarkupNode.GetIsPlaneValid():
      logging.warning("Cannot apply, plane is not defined")
      return

    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    self.observeSegmentation(False)
    self.logic.apply(self.segmentMarkupNode, self.segmentModel,
      self.scriptedEffect.parameter("Text"),
      self.scriptedEffect.doubleParameter("TextDepth"),
      self.scriptedEffect.parameter("Mode"))
    self.reset()
    # Create model node prior to markup node for display order
    self.createNewModelNode()
    self.createNewMarkupNode()
    self.markupsPlacementToggle.setCurrentNode(self.segmentMarkupNode)
    self.observeSegmentation(True)
    qt.QApplication.restoreOverrideCursor()

  def observeSegmentation(self, observationEnabled):
    import vtkSegmentationCore
    if self.scriptedEffect.parameterSetNode().GetSegmentationNode():
      segmentation = self.scriptedEffect.parameterSetNode().GetSegmentationNode().GetSegmentation()
    else:
      segmentation = None
    # Remove old observer
    if self.observedSegmentation:
      self.observedSegmentation.RemoveObserver(self.segmentObserver)
      self.segmentObserver = None
    # Add new observer
    if observationEnabled and segmentation is not None:
      self.observedSegmentation = segmentation
      self.segmentObserver = self.observedSegmentation.AddObserver(vtkSegmentationCore.vtkSegmentation.SegmentModified,
                                                                   self.onSegmentModified)

  def createNewModelNode(self):
    if self.segmentModel is None:
      self.segmentModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
      self.segmentModel.SetName("SegmentEditorEngraveModel")

      modelDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")
      self.logic.setUpModelDisplayNode(modelDisplayNode)
      self.segmentModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
      self.segmentModel.SetSelectable(False) # prevent interference with markup placement

      self.segmentModel.GetDisplayNode().Visibility2DOn()

  def createNewMarkupNode(self):
    # Create empty markup fiducial node
    if self.segmentMarkupNode is None:
      self.segmentMarkupNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsPlaneNode", "E")
      self.segmentMarkupNode.CreateDefaultDisplayNodes()
      self.segmentMarkupNode.SetPlaneType(slicer.vtkMRMLMarkupsPlaneNode.PlaneTypePointNormal)
      self.segmentMarkupNode.SetPlaneBounds(-30, 30, -10, 10)
      displayNode = self.segmentMarkupNode.GetDisplayNode()
      # Do not show plane outline or fill, just control points, and then the positioning arrows
      displayNode.SetPointLabelsVisibility(False)
      displayNode.SetOutlineVisibility(True)
      displayNode.SetFillVisibility(True)
      displayNode.SetFillOpacity(0.2)
      displayNode.SetHandlesInteractive(True)
      displayNode.SetSnapMode(slicer.vtkMRMLMarkupsDisplayNode.SnapModeToVisibleSurface)

      self.setAndObserveSegmentMarkupNode(self.segmentMarkupNode)
      self.updateGUIFromMRML()

  def setAndObserveSegmentMarkupNode(self, segmentMarkupNode):
    if segmentMarkupNode == self.segmentMarkupNode and self.segmentMarkupNodeObservers:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.segmentMarkupNode and self.segmentMarkupNodeObservers:
      for observer in self.segmentMarkupNodeObservers:
        self.segmentMarkupNode.RemoveObserver(observer)
      self.segmentMarkupNodeObservers = []
    # Set and observe new parameter node
    self.segmentMarkupNode = segmentMarkupNode
    if self.segmentMarkupNode:
      if (slicer.app.majorVersion >= 5) or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
        eventIds = [ vtk.vtkCommand.ModifiedEvent,
          slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
          slicer.vtkMRMLMarkupsNode.PointAddedEvent,
          slicer.vtkMRMLMarkupsNode.PointRemovedEvent ]
      else:
        eventIds = [ vtk.vtkCommand.ModifiedEvent ]
      for eventId in eventIds:
        self.segmentMarkupNodeObservers.append(self.segmentMarkupNode.AddObserver(eventId, self.onSegmentMarkupNodeModified))
      self.segmentMarkupNodeObservers.append(
        self.segmentMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.DisplayModifiedEvent, self.onSegmentMarkupDisplayNodeModified))
    # Update GUI
    self.updateModelFromSegmentMarkupNode()

  def onSegmentMarkupNodeModified(self, observer, eventid):
    self.updateModelFromSegmentMarkupNode()
    self.updateGUIFromMRML()

  def onSegmentMarkupDisplayNodeModified(self, observer, eventid):
    self.updateGUIFromMRML()

  def setAndObserveSegmentEditorNode(self, segmentEditorNode):
    if segmentEditorNode == self.segmentEditorNode and self.segmentEditorNodeObserver:
      # no change and node is already observed
      return
      # Remove observer to old parameter node
    if self.segmentEditorNode and self.segmentEditorNodeObserver:
      self.segmentEditorNode.RemoveObserver(self.segmentEditorNodeObserver)
      self.segmentEditorNodeObserver = None
      # Set and observe new parameter node
    self.segmentEditorNode = segmentEditorNode
    if self.segmentEditorNode:
      self.segmentEditorNodeObserver = self.segmentEditorNode.AddObserver(vtk.vtkCommand.ModifiedEvent,
                                                                          self.onSegmentEditorNodeModified)

  def onSegmentEditorNodeModified(self, observer, eventid):
    if self.scriptedEffect.parameterSetNode() is None:
      return

    self.updateGUIFromMRML()

  def updateModelFromSegmentMarkupNode(self):
    if not self.segmentMarkupNode or not self.segmentModel:
      return
    self.logic.updateModel(self.segmentMarkupNode, self.segmentModel,
      self.scriptedEffect.parameter("Text"),
      self.scriptedEffect.doubleParameter("TextDepth"))

    displayNode = self.segmentMarkupNode.GetDisplayNode()
    if displayNode:
      planeFullyDefined = self.segmentMarkupNode.GetIsPlaneValid()
      # only show control points while placing points
      displayNode.SetOpacity(0.0 if planeFullyDefined else 1.0)
      # only show interaction handles when the plane is fully defined
      displayNode.SetHandlesInteractive(planeFullyDefined)


  def interactionNodeModified(self, interactionNode):
    # Override default behavior: keep the effect active if markup placement mode is activated
    pass

  def getNumberOfDefinedControlPoints(self):
    if not self.segmentMarkupNode:
      return 0
    return self.segmentMarkupNode.GetNumberOfDefinedControlPoints()

  def onInteractionResizeEnabled(self, enable):
    if not self.segmentMarkupNode or not self.segmentMarkupNode.GetDisplayNode():
      return
    segmentMarkupDisplayNode = self.segmentMarkupNode.GetDisplayNode()
    if enable:
      segmentMarkupDisplayNode.SetHandlesInteractive(True)
    segmentMarkupDisplayNode.SetScaleHandleVisibility(enable)

  def onInteractionMoveEnabled(self, enable):
    if not self.segmentMarkupNode or not self.segmentMarkupNode.GetDisplayNode():
      return
    segmentMarkupDisplayNode = self.segmentMarkupNode.GetDisplayNode()
    if enable:
      segmentMarkupDisplayNode.SetHandlesInteractive(True)
    segmentMarkupDisplayNode.SetTranslationHandleVisibility(enable)
    segmentMarkupDisplayNode.SetRotationHandleVisibility(enable)


class EngraveLogic:

  def __init__(self, scriptedEffect):
    self.scriptedEffect = scriptedEffect
    self.vectorText = vtk.vtkVectorText()

    self.scaleAndTranslateTransform = vtk.vtkTransform()

    self.polyScaleTransform = vtk.vtkTransformPolyDataFilter()
    self.polyScaleTransform.SetTransform(self.scaleAndTranslateTransform)
    self.polyScaleTransform.SetInputConnection(self.vectorText.GetOutputPort())

    # get normals
    self.polyDataNormals = vtk.vtkPolyDataNormals()  # computes cell normals
    self.polyDataNormals.SetInputConnection(self.polyScaleTransform.GetOutputPort())
    self.polyDataNormals.ConsistencyOn()

    # extrude the marker to underside of valve
    self.extrusion = vtk.vtkLinearExtrusionFilter()
    self.extrusion.SetInputConnection(self.polyDataNormals.GetOutputPort())
    self.extrusion.SetExtrusionTypeToVectorExtrusion()
    self.extrusion.CappingOn()

  def setUpModelDisplayNode(self, modelDisplayNode):
    modelDisplayNode.SetColor(1.0, 1.0, 0.0)
    modelDisplayNode.BackfaceCullingOff()
    modelDisplayNode.Visibility2DOn()
    modelDisplayNode.SetSliceIntersectionThickness(2)
    modelDisplayNode.SetOpacity(1.0)  # Between 0-1, 1 being opaque

  def updateModel(self, inputMarkup, outputModel, text, textDepth):

    """
    Update model to enclose all points in the input markup list
    """

    if not inputMarkup.GetIsPlaneValid():
      outputModel.SetAndObserveMesh(None)
      return

    self.vectorText.SetText(text)

    planeToWorldMatrix = vtk.vtkMatrix4x4()
    if (slicer.app.majorVersion >= 5) or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
      inputMarkup.GetObjectToWorldMatrix(planeToWorldMatrix)
    else:
      inputMarkup.GetPlaneToWorldMatrix(planeToWorldMatrix)

    self.vectorText.Update()
    unscaledBounds = self.vectorText.GetOutput().GetBounds()
    planeBounds = inputMarkup.GetPlaneBounds()
    scale = [(planeBounds[1]-planeBounds[0])/(unscaledBounds[1]-unscaledBounds[0]),
             (planeBounds[3]-planeBounds[2])/(unscaledBounds[3]-unscaledBounds[2]),
             1]

    # scale marker and translate to desired location on skirt
    self.scaleAndTranslateTransform.Identity()
    self.scaleAndTranslateTransform.Concatenate(planeToWorldMatrix)
    self.scaleAndTranslateTransform.Translate(planeBounds[0], planeBounds[2], 0)
    self.scaleAndTranslateTransform.Scale(scale)
    self.scaleAndTranslateTransform.Translate(0, 0, -textDepth/2.0)  # center the unit letter

    # extrude the marker to underside of valve
    planeNormal = [planeToWorldMatrix.GetElement(0,2), planeToWorldMatrix.GetElement(1,2), planeToWorldMatrix.GetElement(2,2)]
    self.extrusion.SetVector(planeNormal)
    self.extrusion.SetScaleFactor(textDepth)

    self.extrusion.Update()

    if not outputModel.GetPolyData():
      outputModel.SetAndObserveMesh(vtk.vtkPolyData())

    # Need to pause render, to prevent rendering pipeline updates during DeepCopy.
    # (Details: During deepcopy, Modified() is called before the copy is fully completed,
    # which can trigger a rendering pipeline update. During that update, the
    # polydata that is still in inconsistent state is used, which can cause
    # application crash.)
    slicer.app.pauseRender()
    outputModel.GetPolyData().DeepCopy(self.extrusion.GetOutput())
    slicer.app.resumeRender()

  def apply(self, segmentMarkupNode, segmentModel, text, textDepth, mode):

    self.updateModel(segmentMarkupNode, segmentModel, text, textDepth)

    import vtkSegmentationCore

    if not segmentMarkupNode:
      raise AttributeError(f"{self.__class__.__name__}: segment markup node not set.")
    if not segmentModel:
      raise AttributeError(f"{self.__class__.__name__}: segment model not set.")

    if segmentMarkupNode and segmentModel.GetPolyData().GetNumberOfCells() > 0:
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      if not segmentationNode:
        raise AttributeError(f"{self.__class__.__name__}: Segmentation node not set.")

      modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()
      if not modifierLabelmap:
        raise AttributeError("{}: ModifierLabelmap not set. This can happen for various reasons:\n"
                             "No master volume set for segmentation,\n"
                             "No existing segments for segmentation, or\n"
                             "No referenceImageGeometry is specified in the segmentation".format(self.__class__.__name__))

      WorldToModifierLabelmapIjkTransform = vtk.vtkTransform()

      WorldToModifierLabelmapIjkTransformer = vtk.vtkTransformPolyDataFilter()
      WorldToModifierLabelmapIjkTransformer.SetTransform(WorldToModifierLabelmapIjkTransform)
      WorldToModifierLabelmapIjkTransformer.SetInputConnection(segmentModel.GetPolyDataConnection())

      segmentationToSegmentationIjkTransformMatrix = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(segmentationToSegmentationIjkTransformMatrix)
      segmentationToSegmentationIjkTransformMatrix.Invert()
      WorldToModifierLabelmapIjkTransform.Concatenate(segmentationToSegmentationIjkTransformMatrix)

      worldToSegmentationTransformMatrix = vtk.vtkMatrix4x4()
      slicer.vtkMRMLTransformNode.GetMatrixTransformBetweenNodes(None, segmentationNode.GetParentTransformNode(),
                                                                 worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransform.Concatenate(worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransformer.Update()

      polyToStencil = vtk.vtkPolyDataToImageStencil()
      polyToStencil.SetOutputSpacing(1.0, 1.0, 1.0)
      polyToStencil.SetInputConnection(WorldToModifierLabelmapIjkTransformer.GetOutputPort())
      boundsIjk = WorldToModifierLabelmapIjkTransformer.GetOutput().GetBounds()
      modifierLabelmapExtent = self.scriptedEffect.modifierLabelmap().GetExtent()
      polyToStencil.SetOutputWholeExtent(modifierLabelmapExtent[0], modifierLabelmapExtent[1],
                                         modifierLabelmapExtent[2], modifierLabelmapExtent[3],
                                         int(round(boundsIjk[4])), int(round(boundsIjk[5])))
      polyToStencil.Update()

      stencilData = polyToStencil.GetOutput()
      stencilExtent = [0, -1, 0, -1, 0, -1]
      stencilData.SetExtent(stencilExtent)

      stencilToImage = vtk.vtkImageStencilToImage()
      stencilToImage.SetInputConnection(polyToStencil.GetOutputPort())
      stencilToImage.SetInsideValue(1.0)
      stencilToImage.SetOutsideValue(0.0)
      stencilToImage.SetOutputScalarType(modifierLabelmap.GetScalarType())

      stencilPositioner = vtk.vtkImageChangeInformation()
      stencilPositioner.SetInputConnection(stencilToImage.GetOutputPort())
      stencilPositioner.SetOutputSpacing(modifierLabelmap.GetSpacing())
      stencilPositioner.SetOutputOrigin(modifierLabelmap.GetOrigin())

      stencilPositioner.Update()
      orientedStencilPositionerOutput = vtkSegmentationCore.vtkOrientedImageData()
      orientedStencilPositionerOutput.ShallowCopy(stencilToImage.GetOutput())
      imageToWorld = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(imageToWorld)
      orientedStencilPositionerOutput.SetImageToWorldMatrix(imageToWorld)

      vtkSegmentationCore.vtkOrientedImageDataResample.ModifyImage(
        modifierLabelmap, orientedStencilPositionerOutput,
        vtkSegmentationCore.vtkOrientedImageDataResample.OPERATION_MAXIMUM)

      modeName = self.scriptedEffect.parameter("Mode")
      if modeName == "EMBOSS":
        mode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd
      elif modeName == "ENGRAVE":
        mode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeRemove
      else:
        logging.error("Invalid mode: "+modeName+" (valid modes: EMBOSS, ENGRAVE)")
      self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, mode)

      # get plane parameters as space-separated string list
      planeParameters = []
      if segmentMarkupNode.GetIsPlaneValid():
        planeParameters.extend(segmentMarkupNode.GetOriginWorld())
        xAxis = [1, 0, 0]
        yAxis = [0, 1, 0]
        zAxis = [0, 0, 1]
        segmentMarkupNode.GetAxesWorld(xAxis, yAxis, zAxis)
        planeParameters.extend(xAxis)
        planeParameters.extend(yAxis)
        planeParameters.extend(zAxis)
        planeParameters.extend(segmentMarkupNode.GetPlaneBounds())
      planeParametersString = ' '.join(map(str, planeParameters))

      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      segment.SetTag("EngraveEffectPlaneParameters", planeParametersString)
