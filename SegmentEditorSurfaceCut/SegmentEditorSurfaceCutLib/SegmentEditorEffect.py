import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses markup fiducials to segment the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Surface cut'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

    # Effect-specific members
    self.segmentMarkupNode = None
    self.segmentMarkupNodeObserver = None
    self.segmentEditorNode = None
    self.segmentEditorNodeObserver = None
    self.segmentModel = None
    self.observedSegmentation = None
    self.segmentObserver = None
    self.buttonToOperationNameMap = {}

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
    return """<html>Use markup fiducials to fill a segment<br>. The surface is generated from the placed points.
</html>"""

  def setupOptionsFrame(self):
    self.operationRadioButtons = []

    #Operation buttons
    self.eraseInsideButton = qt.QRadioButton("Erase inside")
    self.operationRadioButtons.append(self.eraseInsideButton)
    self.buttonToOperationNameMap[self.eraseInsideButton] = 'ERASE_INSIDE'

    self.eraseOutsideButton = qt.QRadioButton("Erase outside")
    self.operationRadioButtons.append(self.eraseOutsideButton)
    self.buttonToOperationNameMap[self.eraseOutsideButton] = 'ERASE_OUTSIDE'

    self.fillInsideButton = qt.QRadioButton("Fill inside")
    self.operationRadioButtons.append(self.fillInsideButton)
    self.buttonToOperationNameMap[self.fillInsideButton] = 'FILL_INSIDE'

    self.fillOutsideButton = qt.QRadioButton("Fill outside")
    self.operationRadioButtons.append(self.fillOutsideButton)
    self.buttonToOperationNameMap[self.fillOutsideButton] = 'FILL_OUTSIDE'

    self.setButton = qt.QRadioButton("Set")
    self.operationRadioButtons.append(self.setButton)
    self.buttonToOperationNameMap[self.setButton] = 'SET'
    self.setButton.setVisible(False)

    #Operation buttons layout
    operationLayout = qt.QGridLayout()
    operationLayout.addWidget(self.eraseInsideButton, 0, 0)
    operationLayout.addWidget(self.eraseOutsideButton, 1, 0)
    operationLayout.addWidget(self.fillInsideButton, 0, 1)
    operationLayout.addWidget(self.fillOutsideButton, 1, 1)
    operationLayout.addWidget(self.setButton, 0, 2)

    self.operationRadioButtons[2].setChecked(True)
    self.scriptedEffect.addLabeledOptionsWidget("Operation:", operationLayout)

    #Fiducial Placement widget
    self.fiducialPlacementToggle = slicer.qSlicerMarkupsPlaceWidget()
    self.fiducialPlacementToggle.setMRMLScene(slicer.mrmlScene)
    self.fiducialPlacementToggle.placeMultipleMarkups = self.fiducialPlacementToggle.ForcePlaceMultipleMarkups
    self.fiducialPlacementToggle.buttonsVisible = False
    self.fiducialPlacementToggle.show()
    self.fiducialPlacementToggle.placeButton().show()
    self.fiducialPlacementToggle.deleteButton().show()

    # Edit surface button
    self.editButton = qt.QPushButton("Edit previous group")
    self.editButton.objectName = self.__class__.__name__ + 'Edit'
    self.editButton.setToolTip("Edit the previously placed group of fiducials.")

    fiducialAction = qt.QHBoxLayout()
    fiducialAction.addWidget(self.fiducialPlacementToggle)
    fiducialAction.addWidget(self.editButton)
    self.scriptedEffect.addLabeledOptionsWidget("Fiducial Placement: ", fiducialAction)

    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Generate surface from markup fiducials.")
    self.scriptedEffect.addOptionsWidget(self.applyButton)

    # Cancel button
    self.cancelButton = qt.QPushButton("Cancel")
    self.cancelButton.objectName = self.__class__.__name__ + 'Cancel'
    self.cancelButton.setToolTip("Clear fiducials and remove from scene.")

    #Finish action buttons
    finishAction = qt.QHBoxLayout()
    finishAction.addWidget(self.cancelButton)
    finishAction.addWidget(self.applyButton)
    self.scriptedEffect.addOptionsWidget(finishAction)

    # connections
    for button in self.operationRadioButtons:
      button.connect('toggled(bool)',
      lambda toggle, widget=self.buttonToOperationNameMap[button]: self.onOperationSelectionChanged(widget, toggle))
    self.applyButton.connect('clicked()', self.onApply)
    self.cancelButton.connect('clicked()', self.onCancel)
    self.editButton.connect('clicked()', self.onEdit)
    self.fiducialPlacementToggle.placeButton().clicked.connect(self.onFiducialPlacementToggleChanged)

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

  def deactivate(self):
    self.reset()
    self.observeSegmentation(False)
    self.setAndObserveSegmentEditorNode(None)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("Operation", "FILL_INSIDE")

  def updateGUIFromMRML(self):
    if self.segmentMarkupNode:
      self.cancelButton.setEnabled(self.segmentMarkupNode.GetNumberOfFiducials() is not 0)
      self.applyButton.setEnabled(self.segmentMarkupNode.GetNumberOfFiducials() >= 3)

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    if segmentID and segmentationNode:
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      self.editButton.setVisible(segment.HasTag("fP"))
      self.setButton.setVisible(not self.scriptedEffect.selectedSegmentLabelmap().IsEmpty())

  #
  # Effect specific methods (the above ones are the API methods to override)
  #

  def onOperationSelectionChanged(self, operationName, toggle):
    if not toggle:
      return
    self.scriptedEffect.setParameter("Operation", operationName)

  def onFiducialPlacementToggleChanged(self):
    if self.fiducialPlacementToggle.placeButton().isChecked():
      # Create empty model node
      if self.segmentModel is None:
        self.segmentModel = slicer.vtkMRMLModelNode()
        slicer.mrmlScene.AddNode(self.segmentModel)

      # Create empty markup fiducial node
      if self.segmentMarkupNode is None:
        self.createNewMarkupNode()
        self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)

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
    fPosNum = vtk.mutable("0")
    segment.GetTag("fP", fPosStr)
    segment.GetTag("fN", fPosNum)

    import numpy
    fPos = numpy.fromstring(str(fPosStr), dtype='float64').reshape((int(fPosNum), 3))
    for i in xrange(int(fPosNum)):
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

    import vtkSegmentationCorePython as vtkSegmentationCore

    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

    if self.segmentMarkupNode and (self.segmentModel.GetPolyData().GetNumberOfPolys() > 0):
      self.observeSegmentation(False)
      operationName = self.scriptedEffect.parameter("Operation")
      modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      WorldToModifierLabelmapIjkTransform = vtk.vtkTransform()

      WorldToModifierLabelmapIjkTransformer = vtk.vtkTransformPolyDataFilter()
      WorldToModifierLabelmapIjkTransformer.SetTransform(WorldToModifierLabelmapIjkTransform)
      WorldToModifierLabelmapIjkTransformer.SetInputConnection(self.segmentModel.GetPolyDataConnection())

      segmentationToSegmentationIjkTransformMatrix = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(segmentationToSegmentationIjkTransformMatrix)
      segmentationToSegmentationIjkTransformMatrix.Invert()
      WorldToModifierLabelmapIjkTransform.Concatenate(segmentationToSegmentationIjkTransformMatrix)

      worldToSegmentationTransformMatrix = vtk.vtkMatrix4x4()
      slicer.vtkMRMLTransformNode.GetMatrixTransformBetweenNodes(None, segmentationNode.GetParentTransformNode(), worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransform.Concatenate(worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransformer.Update()

      polyToStencil = vtk.vtkPolyDataToImageStencil()
      polyToStencil.SetOutputSpacing(1.0, 1.0, 1.0)
      polyToStencil.SetInputConnection(WorldToModifierLabelmapIjkTransformer.GetOutputPort())
      boundsIjk = WorldToModifierLabelmapIjkTransformer.GetOutput().GetBounds()
      modifierLabelmapExtent = self.scriptedEffect.modifierLabelmap().GetExtent()
      polyToStencil.SetOutputWholeExtent(modifierLabelmapExtent[0], modifierLabelmapExtent[1], modifierLabelmapExtent[2], modifierLabelmapExtent[3], int(round(boundsIjk[4])), int(round(boundsIjk[5])))
      polyToStencil.Update()

      stencilData = polyToStencil.GetOutput()
      stencilExtent = [0, -1, 0, -1, 0, -1]
      stencilData.SetExtent(stencilExtent)

      stencilToImage = vtk.vtkImageStencilToImage()
      stencilToImage.SetInputConnection(polyToStencil.GetOutputPort())
      if operationName in ("FILL_INSIDE", "ERASE_INSIDE", "SET"):
        stencilToImage.SetInsideValue(1.0)
        stencilToImage.SetOutsideValue(0.0)
      else:
        stencilToImage.SetInsideValue(0.0)
        stencilToImage.SetOutsideValue(1.0)
      stencilToImage.SetOutputScalarType(modifierLabelmap.GetScalarType())

      stencilPositioner = vtk.vtkImageChangeInformation()
      stencilPositioner.SetInputConnection(stencilToImage.GetOutputPort())
      stencilPositioner.SetOutputSpacing(modifierLabelmap.GetSpacing())
      stencilPositioner.SetOutputOrigin(modifierLabelmap.GetOrigin())

      stencilPositioner.Update()
      orientedStencilPositionerOuput = vtkSegmentationCore.vtkOrientedImageData()
      orientedStencilPositionerOuput.ShallowCopy(stencilToImage.GetOutput())
      imageToWorld = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(imageToWorld)
      orientedStencilPositionerOuput.SetImageToWorldMatrix(imageToWorld)

      vtkSegmentationCore.vtkOrientedImageDataResample.ModifyImage(modifierLabelmap, orientedStencilPositionerOuput, vtkSegmentationCore.vtkOrientedImageDataResample.OPERATION_MAXIMUM)

      modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd
      if operationName == "ERASE_INSIDE" or operationName == "ERASE_OUTSIDE":
        modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeRemove
      elif operationName == "SET":
        modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeSet

      self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, modMode)

      import numpy
      n = self.segmentMarkupNode.GetNumberOfFiducials()
      # get fiducial positions
      fPos = numpy.zeros((n, 3))
      for i in xrange(n):
        coord = [0.0, 0.0, 0.0]
        self.segmentMarkupNode.GetNthFiducialPosition(i, coord)
        fPos[i] = coord
      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      segment.SetTag("fP", fPos.tostring())
      segment.SetTag("fN", n)

    self.reset()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
    self.observeSegmentation(True)
    qt.QApplication.restoreOverrideCursor()

  def observeSegmentation(self, observationEnabled):
    import vtkSegmentationCorePython as vtkSegmentationCore
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
      self.segmentObserver = self.observedSegmentation.AddObserver(vtkSegmentationCore.vtkSegmentation.SegmentModified, self.onSegmentModified)

  def createNewMarkupNode(self):
    # Create empty markup fiducial node
    if self.segmentMarkupNode is None:
      displayNode = slicer.vtkMRMLMarkupsDisplayNode()
      displayNode.SetTextScale(0)
      slicer.mrmlScene.AddNode(displayNode)
      self.segmentMarkupNode = slicer.vtkMRMLMarkupsFiducialNode()
      self.segmentMarkupNode.SetName('C')
      slicer.mrmlScene.AddNode(self.segmentMarkupNode)
      self.segmentMarkupNode.SetAndObserveDisplayNodeID(displayNode.GetID())
      self.setAndObserveSegmentMarkupNode(self.segmentMarkupNode)
      self.updateGUIFromMRML()


  def setAndObserveSegmentMarkupNode(self, segmentMarkupNode):
    if segmentMarkupNode == self.segmentMarkupNode and self.segmentMarkupNodeObserver:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.segmentMarkupNode and self.segmentMarkupNodeObserver:
      self.segmentMarkupNode.RemoveObserver(self.segmentMarkupNodeObserver)
      self.segmentMarkupNodeObserver = None
    # Set and observe new parameter node
    self.segmentMarkupNode = segmentMarkupNode
    if self.segmentMarkupNode:
      self.segmentMarkupNodeObserver = self.segmentMarkupNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onSegmentMarkupNodeModified)
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
      self.segmentEditorNodeObserver = self.segmentEditorNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onSegmentEditorNodeModified)

  def onSegmentEditorNodeModified(self, observer, eventid):
    # Get color of edited segment
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    if segmentID and self.segmentModel:
      r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()
      if (r, g, b) != self.segmentModel.GetDisplayNode().GetColor():
        self.segmentModel.GetDisplayNode().SetColor(r, g, b)  # Edited segment color

    self.updateGUIFromMRML()

  def updateModelFromSegmentMarkupNode(self):
    if not self.segmentMarkupNode or not self.segmentModel:
      return
    self.updateModelFromMarkup(self.segmentMarkupNode, self.segmentModel)

  def updateModelFromMarkup(self, inputMarkup, outputModel):
    """
    Update model to enclose all points in the input markup list
    """

    # Delaunay triangulation is robust and creates nice smooth surfaces from a small number of points,
    # however it can only generate convex surfaces robustly.
    useDelaunay = True

    # Create polydata point set from markup points

    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    numberOfPoints = inputMarkup.GetNumberOfFiducials()

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if useDelaunay:
      if numberOfPoints < 3:
        return
    else:
      if numberOfPoints < 10:
        return

    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]

    for i in range(numberOfPoints):
      inputMarkup.GetNthFiducialPosition(i, new_coord)
      points.SetPoint(i, new_coord)

    cellArray.InsertNextCell(numberOfPoints)
    for i in range(numberOfPoints):
      cellArray.InsertCellPoint(i)

    pointPolyData = vtk.vtkPolyData()
    pointPolyData.SetLines(cellArray)
    pointPolyData.SetPoints(points)

    # Create surface from point set

    if useDelaunay:

      delaunay = vtk.vtkDelaunay3D()
      delaunay.SetInputData(pointPolyData)

      surfaceFilter = vtk.vtkDataSetSurfaceFilter()
      surfaceFilter.SetInputConnection(delaunay.GetOutputPort())

      smoother = vtk.vtkButterflySubdivisionFilter()
      smoother.SetInputConnection(surfaceFilter.GetOutputPort())
      smoother.SetNumberOfSubdivisions(3)
      smoother.Update()

      outputModel.SetPolyDataConnection(smoother.GetOutputPort())

    else:

      surf = vtk.vtkSurfaceReconstructionFilter()
      surf.SetInputData(pointPolyData)
      surf.SetNeighborhoodSize(20)
      surf.SetSampleSpacing(
        80)  # lower value follows the small details more closely but more dense pointset is needed as input

      cf = vtk.vtkContourFilter()
      cf.SetInputConnection(surf.GetOutputPort())
      cf.SetValue(0, 0.0)

      # Sometimes the contouring algorithm can create a volume whose gradient
      # vector and ordering of polygon (using the right hand rule) are
      # inconsistent. vtkReverseSense cures this problem.
      reverse = vtk.vtkReverseSense()
      reverse.SetInputConnection(cf.GetOutputPort())
      reverse.ReverseCellsOff()
      reverse.ReverseNormalsOff()

      outputModel.SetPolyDataConnection(reverse.GetOutputPort())

    # Create default model display node if does not exist yet
    if not outputModel.GetDisplayNode():
      modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")

      # Get color of edited segment
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()

      modelDisplayNode.SetColor(r, g, b)  # Edited segment color
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(2)
      modelDisplayNode.SetOpacity(0.3)  # Between 0-1, 1 being opaque
      slicer.mrmlScene.AddNode(modelDisplayNode)
      outputModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

    outputModel.GetDisplayNode().SliceIntersectionVisibilityOn()

    outputModel.Modified()

  def interactionNodeModified(self, interactionNode):
    # Override default behavior: keep the effect active if markup placement mode is activated
    pass
