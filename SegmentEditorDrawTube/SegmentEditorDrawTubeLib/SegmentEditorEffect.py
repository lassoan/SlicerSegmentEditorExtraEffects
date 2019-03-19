import os
import vtk, qt, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses markup fiducials to segment the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Draw tube'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

    self.logic = DrawTubeLogic(scriptedEffect)

    # Effect-specific members
    self.segmentMarkupNode = None
    self.segmentMarkupNodeObservers = []
    self.segmentEditorNode = None
    self.segmentEditorNodeObserver = None
    self.segmentModel = None
    self.observedSegmentation = None
    self.segmentObserver = None
    self.buttonToInterpolationTypeMap = {}

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
    return """<html>Use markup fiducials to create a tube<br>. The tube is generated to connect the placed points.
</html>"""

  def setupOptionsFrame(self):
    self.interpolationRadioButtons = []

    # Fiducial Placement widget
    self.fiducialPlacementToggle = slicer.qSlicerMarkupsPlaceWidget()
    self.fiducialPlacementToggle.setMRMLScene(slicer.mrmlScene)
    self.fiducialPlacementToggle.placeMultipleMarkups = self.fiducialPlacementToggle.ForcePlaceMultipleMarkups
    self.fiducialPlacementToggle.buttonsVisible = False
    self.fiducialPlacementToggle.show()
    self.fiducialPlacementToggle.placeButton().show()
    self.fiducialPlacementToggle.deleteButton().show()

    # Edit surface button
    self.editButton = qt.QPushButton("Edit")
    self.editButton.objectName = self.__class__.__name__ + 'Edit'
    self.editButton.setToolTip("Edit the previously placed group of fiducials.")

    fiducialActionLayout = qt.QHBoxLayout()
    fiducialActionLayout.addWidget(self.fiducialPlacementToggle)
    fiducialActionLayout.addWidget(self.editButton)
    self.scriptedEffect.addLabeledOptionsWidget("Fiducial Placement: ", fiducialActionLayout)
    
    # Radius spinbox
    self.radiusSpinBox = slicer.qMRMLSpinBox()
    self.radiusSpinBox.value = self.logic.radius
    self.radiusSpinBox.quantity = 'length'
    self.radiusSpinBox.unitAwareProperties = slicer.qMRMLSpinBox.MaximumValue | slicer.qMRMLSpinBox.Precision | slicer.qMRMLSpinBox.Prefix | slicer.qMRMLSpinBox.Suffix
    self.scriptedEffect.addLabeledOptionsWidget("Radius: ", self.radiusSpinBox)

    # Interpolation buttons
    self.piecewiseLinearButton = qt.QRadioButton("Piecewise linear")
    self.interpolationRadioButtons.append(self.piecewiseLinearButton)
    self.buttonToInterpolationTypeMap[self.piecewiseLinearButton] = "LINEAR"

    self.cardinalSplineButton = qt.QRadioButton("Cardinal spline")
    self.interpolationRadioButtons.append(self.cardinalSplineButton)
    self.buttonToInterpolationTypeMap[self.cardinalSplineButton] = "CARDINAL_SPLINE"

    self.kochanekSplineButton = qt.QRadioButton("Kochanek spline")
    self.interpolationRadioButtons.append(self.kochanekSplineButton)
    self.buttonToInterpolationTypeMap[self.kochanekSplineButton] = "KOCHANEK_SPLINE"

    self.globalPolynomialButton = qt.QRadioButton("Global polynomial")
    self.interpolationRadioButtons.append(self.globalPolynomialButton)
    self.buttonToInterpolationTypeMap[self.globalPolynomialButton] = "GLOBAL_POLYNOMIAL"

    self.movingPolynomialButton = qt.QRadioButton("Moving polynomial")
    self.interpolationRadioButtons.append(self.movingPolynomialButton)
    self.buttonToInterpolationTypeMap[self.movingPolynomialButton] = "MOVING_POLYNOMIAL"

    # Segments per point spinbox
    self.numberOfLineSegmentsSpinBox = qt.QSpinBox()
    self.numberOfLineSegmentsSpinBox.value = 15
    # To keep GUI simple, we do not show numberOfLineSegmentsSpinBox.
    # Default value should work for most cases and modules can programmatically change this value, if needed.
    # If user feedback confirms that this parameter must be exposed then the next line can be uncommented.
    # self.scriptedEffect.addLabeledOptionsWidget("Segments between points: ", self.numberOfLineSegmentsSpinBox)
    
    # Interpolation buttons layout
    interpolationLayout = qt.QGridLayout()
    interpolationLayout.addWidget(self.piecewiseLinearButton, 0, 0)
    interpolationLayout.addWidget(self.cardinalSplineButton, 1, 0)
    interpolationLayout.addWidget(self.kochanekSplineButton, 0, 1)
    interpolationLayout.addWidget(self.globalPolynomialButton, 1, 1)
    interpolationLayout.addWidget(self.movingPolynomialButton, 0, 2)

    self.scriptedEffect.addLabeledOptionsWidget("Interpolation:", interpolationLayout)

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
    for button in self.interpolationRadioButtons:
      button.connect('toggled(bool)',
      lambda toggle, widget=self.buttonToInterpolationTypeMap[button]: self.onInterpolationSelectionChanged(widget, toggle))
    self.applyButton.connect('clicked()', self.onApply)
    self.cancelButton.connect('clicked()', self.onCancel)
    self.editButton.connect('clicked()', self.onEdit)
    self.fiducialPlacementToggle.placeButton().clicked.connect(self.onFiducialPlacementToggleChanged)
    self.radiusSpinBox.connect('valueChanged(double)', self.onRadiusChanged)
    self.numberOfLineSegmentsSpinBox.connect('valueChanged(int)', self.onNumberOfLineSegmentsChanged)

  def activate(self):
    self.scriptedEffect.showEffectCursorInSliceView = False
    # Create empty markup fiducial node
    if not self.segmentMarkupNode:
      self.createNewMarkupNode()
      self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
      self.setAndObserveSegmentMarkupNode(self.segmentMarkupNode)
      self.fiducialPlacementToggle.setPlaceModeEnabled(False)
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
    self.scriptedEffect.setParameterDefault("Interpolation", "MOVING_POLYNOMIAL")
    self.scriptedEffect.setParameterDefault("NumberOfLineSegmentsBetweenControlPoints", 15) 

  def updateGUIFromMRML(self):
    if self.segmentMarkupNode:
      self.cancelButton.setEnabled(self.segmentMarkupNode.GetNumberOfFiducials() is not 0)
      self.applyButton.setEnabled(self.segmentMarkupNode.GetNumberOfFiducials() >= 3)

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    if segmentID and segmentationNode:
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      self.editButton.setVisible(segment.HasTag("DrawTubeEffectMarkupPositions"))

    interpolationButton = [key for key, value in self.buttonToInterpolationTypeMap.iteritems() if value ==
                       self.scriptedEffect.parameter("Interpolation")][0]
    interpolationButton.setChecked(True)

    self.numberOfLineSegmentsSpinBox.value = self.scriptedEffect.integerParameter("NumberOfLineSegmentsBetweenControlPoints")

  #
  # Effect specific methods (the above ones are the API methods to override)
  #

  def onInterpolationSelectionChanged(self, interpolationName, toggle):
    if not toggle:
      return
    self.scriptedEffect.setParameter("Interpolation", interpolationName)
    self.updateModelFromSegmentMarkupNode()

  def onFiducialPlacementToggleChanged(self):
    if self.fiducialPlacementToggle.placeButton().isChecked():
      # Create empty model node
      if self.segmentModel is None:
        self.segmentModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        self.segmentModel.SetName("SegmentEditorDrawTubeModel")

      # Create empty markup fiducial node
      if self.segmentMarkupNode is None:
        self.createNewMarkupNode()
        self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)

  def onRadiusChanged(self, radius):
    self.logic.radius = radius
    self.updateModelFromSegmentMarkupNode()

  def onNumberOfLineSegmentsChanged(self, numberOfLineSegments):
    self.scriptedEffect.setParameter("NumberOfLineSegmentsBetweenControlPoints", numberOfLineSegments)
    self.updateModelFromSegmentMarkupNode()
    
  def onSegmentModified(self, caller, event):
    if not self.editButton.isEnabled() and self.segmentMarkupNode.GetNumberOfFiducials() is not 0:
      self.reset()
      self.createNewMarkupNode()
      self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
    else:
      self.updateGUIFromMRML()

    if self.segmentModel:
      # Get color of edited segment
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      displayNode = segmentationNode.GetDisplayNode()
      if displayNode is None:
        logging.error("preview: Invalid segmentation display node!")
        color = [0.5, 0.5, 0.5]
      if self.segmentModel.GetDisplayNode():
        segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
        r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()
        if (r,g,b) != self.segmentModel.GetDisplayNode().GetColor():
          self.segmentModel.GetDisplayNode().SetColor(r, g, b)  # Edited segment color

  def onCancel(self):
    self.reset()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)

  def onEdit(self):
    # Create empty model node
    if self.segmentModel is None:
      self.segmentModel = slicer.vtkMRMLModelNode()
      slicer.mrmlScene.AddNode(self.segmentModel)

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)

    fPosStr = vtk.mutable("")
    segment.GetTag("DrawTubeEffectMarkupPositions", fPosStr)
    # convert from space-separated list o fnumbers to 1D array
    import numpy
    fPos = numpy.fromstring(str(fPosStr), sep=' ')
    # convert from 1D array (N*3) to 2D array (N,3)
    fPosNum = int(len(fPos)/3)
    fPos = fPos.reshape((fPosNum, 3))
    for i in xrange(fPosNum):
      self.segmentMarkupNode.AddFiducialFromArray(fPos[i])

    self.editButton.setEnabled(False)
    self.updateModelFromSegmentMarkupNode()

  def reset(self):
    if self.fiducialPlacementToggle.placeModeEnabled:
      self.fiducialPlacementToggle.setPlaceModeEnabled(False)

    if not self.editButton.isEnabled():
      self.editButton.setEnabled(True)

    if self.segmentModel:
      slicer.mrmlScene.RemoveNode(self.segmentModel)
      self.segmentModel = None

    if self.segmentMarkupNode:
      slicer.mrmlScene.RemoveNode(self.segmentMarkupNode)
      self.setAndObserveSegmentMarkupNode(None)

  def onApply(self):
    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    self.observeSegmentation(False)
    self.logic.cutSurfaceWithModel(self.segmentMarkupNode, self.segmentModel)
    self.reset()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
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

  def createNewMarkupNode(self):
    # Create empty markup fiducial node
    if self.segmentMarkupNode is None:
      displayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsDisplayNode")
      displayNode.SetTextScale(0)
      self.segmentMarkupNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
      self.segmentMarkupNode.SetName('T')
      self.segmentMarkupNode.SetAndObserveDisplayNodeID(displayNode.GetID())
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
    # Update GUI
    self.updateModelFromSegmentMarkupNode()

  def onSegmentMarkupNodeModified(self, observer, eventid):
    self.updateModelFromSegmentMarkupNode()
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
    # Get color of edited segment
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    if segmentID and self.segmentModel:
      if self.segmentModel.GetDisplayNode():
        r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()
        if (r, g, b) != self.segmentModel.GetDisplayNode().GetColor():
          self.segmentModel.GetDisplayNode().SetColor(r, g, b)  # Edited segment color

    self.updateGUIFromMRML()

  def updateModelFromSegmentMarkupNode(self):
    if not self.segmentMarkupNode or not self.segmentModel:
      return
    self.logic.updateModelFromMarkup(self.segmentMarkupNode, self.segmentModel)

  def interactionNodeModified(self, interactionNode):
    # Override default behavior: keep the effect active if markup placement mode is activated
    pass

class DrawTubeLogic(object):

  def __init__(self, scriptedEffect):
    self.scriptedEffect = scriptedEffect
    self.radius = 1.0
    self.curveGenerator = slicer.vtkCurveGenerator()

  def updateModelFromMarkup(self, inputMarkup, outputModel):
    """
    Update model to enclose all points in the input markup list
    """

    # Create default model display node if does not exist yet
    if not outputModel.GetDisplayNode():
      modelDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")

      # Get color of edited segment
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()

      modelDisplayNode.SetColor(r, g, b)  # Edited segment color
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(2)
      modelDisplayNode.SetOpacity(0.3)  # Between 0-1, 1 being opaque
      outputModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

      outputModel.GetDisplayNode().SliceIntersectionVisibilityOn()

    interpolationName = self.scriptedEffect.parameter("Interpolation")
    polynomialFitType = slicer.vtkMRMLMarkupsToModelNode.MovingLeastSquares
    if interpolationName == "LINEAR":
      interpolationType = slicer.vtkMRMLMarkupsToModelNode.Linear
    elif interpolationName == "CARDINAL_SPLINE":
      interpolationType = slicer.vtkMRMLMarkupsToModelNode.CardinalSpline
    elif interpolationName == "KOCHANEK_SPLINE":
      interpolationType = slicer.vtkMRMLMarkupsToModelNode.KochanekSpline
    elif interpolationName == "GLOBAL_POLYNOMIAL":
      interpolationType = slicer.vtkMRMLMarkupsToModelNode.Polynomial
      polynomialFitType = slicer.vtkMRMLMarkupsToModelNode.GlobalLeastSquares
    elif interpolationName == "MOVING_POLYNOMIAL":
      interpolationType = slicer.vtkMRMLMarkupsToModelNode.Polynomial
      polynomialFitType = slicer.vtkMRMLMarkupsToModelNode.MovingLeastSquares
      
    NumberOfLineSegmentsBetweenControlPoints = self.scriptedEffect.integerParameter("NumberOfLineSegmentsBetweenControlPoints") 

    markupsToModel = slicer.modules.markupstomodel.logic()
    # Create tube from points
    markupsToModel.UpdateOutputCurveModel( inputMarkup, outputModel,
      interpolationType, False, self.radius, 8, NumberOfLineSegmentsBetweenControlPoints, True, 3,
      slicer.vtkMRMLMarkupsToModelNode.RawIndices, self.curveGenerator,
      polynomialFitType )

  def cutSurfaceWithModel(self, segmentMarkupNode, segmentModel):
    import vtkSegmentationCore

    if not segmentMarkupNode:
      raise AttributeError("{}: segment markup node not set.".format(self.__class__.__name__))
    if not segmentModel:
      raise AttributeError("{}: segment model not set.".format(self.__class__.__name__))

    if segmentMarkupNode and segmentModel.GetPolyData().GetNumberOfCells() > 0:
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      if not segmentationNode:
        raise AttributeError("{}: Segmentation node not set.".format(self.__class__.__name__))

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

      self.scriptedEffect.modifySelectedSegmentByLabelmap(
        modifierLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeSet )

      # get fiducial positions as space-separated list
      import numpy
      n = segmentMarkupNode.GetNumberOfFiducials()
      fPos = []
      for i in xrange(n):
        coord = [0.0, 0.0, 0.0]
        segmentMarkupNode.GetNthFiducialPosition(i, coord)
        fPos.extend(coord)
      fPosString = ' '.join(map(str, fPos))

      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      segment.SetTag("DrawTubeEffectMarkupPositions", fPosString)
