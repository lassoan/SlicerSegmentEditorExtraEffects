import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses FastMarching algorithm to partition the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Fast Marching'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)
    self.originalSelectedSegmentLabelmap = None
    self.selectedSegmentId = None
    self.fm = None
    self.totalNumberOfVoxels = 0
    self.voxelVolume = 0

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
    return """<html>Expand the selected segment<br> to regions that have similar intensity.<p>
Only the selected segment is expanded. No background segment is needed.
The effect uses <a href="http://www.spl.harvard.edu/publications/item/view/193">fast marching method</a>.
<p></html>"""

  def setupOptionsFrame(self):

    self.percentMax = ctk.ctkSliderWidget()
    self.percentMax.minimum = 0
    self.percentMax.maximum = 100
    self.percentMax.singleStep = 1
    self.percentMax.value = 10
    self.percentMax.suffix = '%'
    self.percentMax.setToolTip('Approximate volume of the structure to be segmented as percentage of total volume of the master image.'
      ' Segmentation will grow from the seed label until this value is reached')
    self.percentMax.connect('valueChanged(double)', self.percentMaxChanged)
    self.scriptedEffect.addLabeledOptionsWidget("Maximum volume:", self.percentMax)

    self.march = qt.QPushButton("Initialize")
    self.march.setToolTip("Perform the Marching operation into the current label map")
    self.scriptedEffect.addOptionsWidget(self.march)
    self.march.connect('clicked()', self.onMarch)

    self.marcher = ctk.ctkSliderWidget()
    self.marcher.minimum = 0
    self.marcher.maximum = 100
    self.marcher.singleStep = 0.1
    self.marcher.pageStep = 5
    self.marcher.suffix = '%'
    self.marcher.enabled = False
    self.marcher.connect('valueChanged(double)',self.onMarcherChanged)
    self.percentVolume = self.scriptedEffect.addLabeledOptionsWidget("Segment volume:", self.marcher)
    
    self.cancelButton = qt.QPushButton("Cancel")
    self.cancelButton.objectName = self.__class__.__name__ + 'Cancel'
    self.cancelButton.setToolTip("Clear preview and cancel")

    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Replace segment by previewed result")

    finishFrame = qt.QHBoxLayout()
    finishFrame.addWidget(self.cancelButton)
    finishFrame.addWidget(self.applyButton)
    self.scriptedEffect.addOptionsWidget(finishFrame)

    self.cancelButton.connect('clicked()', self.onCancel)
    self.applyButton.connect('clicked()', self.onApply)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("PercentMax", 10)

  def updateGUIFromMRML(self):
    percentMax = self.scriptedEffect.doubleParameter("PercentMax")
    wasBlocked = self.percentMax.blockSignals(True)
    self.percentMax.value = abs(percentMax)
    self.percentMax.blockSignals(wasBlocked)
    enableApplyCancel = self.fm is not None
    self.applyButton.enabled = enableApplyCancel
    self.cancelButton.enabled = enableApplyCancel
    self.marcher.enabled = enableApplyCancel

  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("PercentMax", self.percentMax.value)
        
  def onMarch(self):
    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    try:
      self.reset() # restore initial seeds in the labelmap
      slicer.util.showStatusMessage('Running FastMarching...', 2000)
      self.scriptedEffect.saveStateForUndo()
      self.fastMarching(self.percentMax.value)
      slicer.util.showStatusMessage('FastMarching finished', 2000)
      self.marcher.value = 100
      if self.totalNumberOfVoxels>0:
        self.marcher.enabled = True
    finally:
      qt.QApplication.restoreOverrideCursor()
    self.updateGUIFromMRML()

  def onMarcherChanged(self,value):
    self.updateLabel(value/self.marcher.maximum)

  def percentMaxChanged(self, val):
    self.updateMRMLFromGUI()

  def fastMarching(self,percentMax):

    self.fm = None
    
    # Get master volume image data
    import vtkSegmentationCorePython as vtkSegmentationCore
    masterImageData = self.scriptedEffect.masterVolumeImageData()
    # Get segmentation
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()

    # Cast master image if not short
    if masterImageData.GetScalarType() != vtk.VTK_SHORT:
      imageCast = vtk.vtkImageCast()
      imageCast.SetInputData(masterImageData)
      imageCast.SetOutputScalarTypeToShort()
      imageCast.ClampOverflowOn()
      imageCast.Update()
      masterImageDataShort = vtkSegmentationCore.vtkOrientedImageData()
      masterImageDataShort.ShallowCopy(imageCast.GetOutput()) # Copy image data
      masterImageDataShort.CopyDirections(masterImageData) # Copy geometry
      masterImageData = masterImageDataShort

    if (slicer.app.majorVersion >= 5) or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
      if not self.originalSelectedSegmentLabelmap:
        segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
        segmentationNode.GetSegmentation().SeparateSegmentLabelmap(self.scriptedEffect.parameterSetNode().GetSelectedSegmentID())

    selectedSegmentLabelmap = self.scriptedEffect.selectedSegmentLabelmap()
    
    if not self.originalSelectedSegmentLabelmap:
      self.originalSelectedSegmentLabelmap = vtkSegmentationCore.vtkOrientedImageData()
      self.originalSelectedSegmentLabelmap.DeepCopy(selectedSegmentLabelmap)
      self.selectedSegmentId = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()

    # We need to know exactly the value of the segment voxels, apply threshold to make force the selected label value
    labelValue = 1
    backgroundValue = 0
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(selectedSegmentLabelmap)
    thresh.ThresholdByLower(0)
    thresh.SetInValue(backgroundValue)
    thresh.SetOutValue(labelValue)
    thresh.SetOutputScalarType(vtk.VTK_UNSIGNED_SHORT)
    thresh.Update()
    labelImage = thresh.GetOutput()    
    
    # collect seeds
    dim = masterImageData.GetDimensions()
    # initialize the filter
    self.fm = slicer.vtkPichonFastMarching()
    scalarRange = masterImageData.GetScalarRange()
    depth = scalarRange[1]-scalarRange[0]

    # this is more or less arbitrary; large depth values will bring the
    # algorithm to the knees
    scaleValue = 0
    shiftValue = 0

    if depth>300:
      scaleValue = 300./depth
    if scalarRange[0] < 0:
      shiftValue = scalarRange[0]*-1

    if scaleValue or shiftValue:
      rescale = vtk.vtkImageShiftScale()
      rescale.SetInputData(masterImageData)
      rescale.SetScale(scaleValue)
      rescale.SetShift(shiftValue)
      rescale.Update()
      masterImageData = rescale.GetOutput()
      scalarRange = masterImageData.GetScalarRange()
      depth = scalarRange[1]-scalarRange[0]

    self.fm.init(dim[0], dim[1], dim[2], depth, 1, 1, 1)

    caster = vtk.vtkImageCast()
    caster.SetOutputScalarTypeToShort()
    caster.SetInputData(masterImageData)
    self.fm.SetInputConnection(caster.GetOutputPort())

    # self.fm.SetOutput(labelImage)

    npoints = int(dim[0]*dim[1]*dim[2]*percentMax/100.)

    self.fm.setNPointsEvolution(npoints)
    self.fm.setActiveLabel(labelValue)

    spacing = self.originalSelectedSegmentLabelmap.GetSpacing()
    self.voxelVolume = spacing[0] * spacing[1] * spacing[2]
    self.totalNumberOfVoxels = npoints

    nSeeds = self.fm.addSeedsFromImage(labelImage)
    if nSeeds == 0:
      self.totalNumberOfVoxels = 0
      return
      
    self.fm.Modified()
    self.fm.Update()

    # Need to call show() twice for data to be updated.
    # There are many other issues with the vtkPichonFastMarching filter
    # (expects extents to start at 0, crashes in debug mode, etc).
    self.fm.show(1)
    self.fm.Modified()
    self.fm.Update()

    self.updateLabel(self.marcher.value/self.marcher.maximum)

    logging.info('FastMarching march update completed')
    
  def updateLabel(self,value):
    if not self.fm:
      return
     
    self.fm.show(value)
    self.fm.Modified()
    self.fm.Update()

    import vtkSegmentationCorePython as vtkSegmentationCore
    newSegmentLabelmap = vtkSegmentationCore.vtkOrientedImageData()
    newSegmentLabelmap.ShallowCopy(self.fm.GetOutput())
    newSegmentLabelmap.CopyDirections(self.originalSelectedSegmentLabelmap)
    
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    slicer.vtkSlicerSegmentationsModuleLogic.SetBinaryLabelmapToSegment(newSegmentLabelmap, segmentationNode, self.selectedSegmentId, slicer.vtkSlicerSegmentationsModuleLogic.MODE_REPLACE, newSegmentLabelmap.GetExtent()) 

  def reset(self):

    # If original segment is available then restore that
    if self.originalSelectedSegmentLabelmap:
      import vtkSegmentationCorePython as vtkSegmentationCore
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      slicer.vtkSlicerSegmentationsModuleLogic.SetBinaryLabelmapToSegment(self.originalSelectedSegmentLabelmap, segmentationNode, self.selectedSegmentId, slicer.vtkSlicerSegmentationsModuleLogic.MODE_REPLACE, self.originalSelectedSegmentLabelmap.GetExtent()) 
      
    self.originalSelectedSegmentLabelmap = None
    self.selectedSegmentId = None
    self.fm = None
    
    self.updateGUIFromMRML()

  def onCancel(self):
    self.reset()

  def onApply(self):
    # Apply changes
    import vtkSegmentationCorePython as vtkSegmentationCore
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    if (slicer.app.majorVersion >= 5) or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
      modifierLabelmap = vtkSegmentationCore.vtkOrientedImageData()
      segmentationNode.GetBinaryLabelmapRepresentation(self.selectedSegmentId, modifierLabelmap)
    else:
      modifierLabelmap = segmentationNode.GetBinaryLabelmapRepresentation(self.selectedSegmentId)
    self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeSet)
    self.originalSelectedSegmentLabelmap = None

    self.reset()
    self.scriptedEffect.selectEffect("")
