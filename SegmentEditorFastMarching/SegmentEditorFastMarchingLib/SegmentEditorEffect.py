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
    return """Existing segments are grown to fill the image.
The effect is different from the Grow from seeds effect in that smoothness of structures can be defined, which can prevent leakage.
To segment a single object, create a segment and paint inside and create another segment and paint outside on each axis.
"""

  def setupOptionsFrame(self):

    self.percentMax = ctk.ctkSliderWidget()
    self.percentMax.minimum = 0
    self.percentMax.maximum = 100
    self.percentMax.singleStep = 1
    self.percentMax.value = 30
    self.percentMax.setToolTip('Approximate volume of the structure to be segmented relative to the total volume of the image'
      'Segmentation will grow from the seed label until this value is reached')
    self.percentMax.connect('valueChanged(double)', self.percentMaxChanged)
    self.scriptedEffect.addLabeledOptionsWidget("Expected structure volume as % of image volume:", self.percentMax)

    self.march = qt.QPushButton("March")
    self.march.setToolTip("Perform the Marching operation into the current label map")
    self.scriptedEffect.addOptionsWidget(self.march)
    self.march.connect('clicked()', self.onMarch)

    self.marcher = ctk.ctkSliderWidget()
    self.marcher.minimum = 0
    self.marcher.maximum = 1
    self.marcher.singleStep = 0.01
    self.marcher.enabled = False
    self.marcher.connect('valueChanged(double)',self.onMarcherChanged)
    self.scriptedEffect.addLabeledOptionsWidget("Maximum volume of the structure:", self.marcher)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("PercentMax", 30)

  def updateGUIFromMRML(self):
    percentMax = self.scriptedEffect.doubleParameter("PercentMax")
    wasBlocked = self.percentMax.blockSignals(True)
    self.percentMax.value = abs(percentMax)
    self.percentMax.blockSignals(wasBlocked)

  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("PercentMax", self.percentMax.value)
        
  def onMarch(self):
    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    try:
      slicer.util.showStatusMessage('Running FastMarching...', 2000)
      self.scriptedEffect.saveStateForUndo()
      npoints = self.fastMarching(self.percentMax.value)
      slicer.util.showStatusMessage('FastMarching finished', 2000)
      if npoints:
        self.marcher.minimum = 0
        self.marcher.maximum = npoints
        self.marcher.value = npoints
        self.marcher.singleStep = 1
        self.marcher.enabled = True
    finally:
      qt.QApplication.restoreOverrideCursor()

  def onMarcherChanged(self,value):
    self.updateLabel(value/self.marcher.maximum)

  def percentMaxChanged(self, val):
    pass
    # labelNode = self.getLabelNode()
    # labelImage = EditUtil.getLabelImage()
    # spacing = labelNode.GetSpacing()
    # dim = labelImage.GetDimensions()
    # print dim
    # totalVolume = spacing[0]*dim[0]+spacing[1]*dim[1]+spacing[2]*dim[2]

    # percentVolumeStr = "%.5f" % (totalVolume*val/100.)
    # self.percentVolume.text = '(maximum total volume: '+percentVolumeStr+' mL)'

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

    # Generate merged labelmap as input to Marching
    #mergedImage = vtkSegmentationCore.vtkOrientedImageData()
    #virtual vtkOrientedImageData* GetBinaryLabelmapRepresentation(const std::string segmentId);
    #segmentationNode.GetGenerateMergedLabelmapForAllSegments(mergedImage, vtkSegmentationCore.vtkSegmentation.EXTENT_UNION_OF_SEGMENTS, masterImageData)
    selectedSegmentLabelmap = self.scriptedEffect.selectedSegmentLabelmap()
    
    self.originalSelectedSegmentLabelmap = vtkSegmentationCore.vtkOrientedImageData()
    self.originalSelectedSegmentLabelmap.DeepCopy(selectedSegmentLabelmap)

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
    print dim
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

    print('Input scalar range: '+str(depth))
    self.fm.init(dim[0], dim[1], dim[2], depth, 1, 1, 1)

    caster = vtk.vtkImageCast()
    caster.SetOutputScalarTypeToShort()
    caster.SetInputData(masterImageData)
    self.fm.SetInputConnection(caster.GetOutputPort())

    # self.fm.SetOutput(labelImage)

    npoints = int(dim[0]*dim[1]*dim[2]*percentMax/100.)

    self.fm.setNPointsEvolution(npoints)
    self.fm.setActiveLabel(labelValue)

    nSeeds = self.fm.addSeedsFromImage(labelImage)
    if nSeeds == 0:
      return 0

    self.fm.Modified()
    self.fm.Update()

    # TODO: need to call show() twice for data to be updated
    self.fm.show(1)
    self.fm.Modified()
    self.fm.Update()

    self.fm.show(1)
    self.fm.Modified()
    self.fm.Update()

    #self.undoRedo.saveState()

    #EditUtil.getLabelImage().DeepCopy(self.fm.GetOutput())
    #EditUtil.markVolumeNodeAsModified(self.sliceLogic.GetLabelLayer().GetVolumeNode())
    # print('FastMarching output image: '+str(output))
    print('FastMarching march update completed')

    return npoints

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
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID() 
    slicer.vtkSlicerSegmentationsModuleLogic.SetBinaryLabelmapToSegment(newSegmentLabelmap, segmentationNode, segmentID, slicer.vtkSlicerSegmentationsModuleLogic.MODE_REPLACE, newSegmentLabelmap.GetExtent()) 
