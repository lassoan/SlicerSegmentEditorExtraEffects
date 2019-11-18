import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *
import vtkITK
import SimpleITK as sitk
import sitkUtils
import math

class SegmentEditorEffect(SegmentEditorThresholdEffect):
  """ LocalThresholdEffect is an effect that can perform a localized threshold when the user ctrl-clicks on the image.
  """

  def __init__(self, scriptedEffect):
    SegmentEditorThresholdEffect.__init__(self, scriptedEffect)
    scriptedEffect.name = 'Local Threshold'

  def clone(self):
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\','/'))
    return clonedEffect

  def icon(self):
    iconPath = os.path.join(os.path.dirname(__file__), 'SegmentEditorEffect.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return """<html>
Fill segment in a selected region based on master volume intensity range<br>.
<p>
  <b>Ctrl + left-click:</b> Add the selected island within the threshold to the segment.
</p>
<p>
  Options:
  <ul style="feature: 0">
    <li><b>Feature size:</b> Prevent leaks through features that are smaller than the specified size. Also used in WaterShed to specify the gradient magnitude.</li>
    <li><b>Segmentation algorithm:</b> Algorithm used to perform the selection on the specified region.</li>
    <li><b>ROI:</b> Region of interest that the threshold segmentation will be perfomed within. Selecting a smaller region will reduce leaks and improve speed.</li>
  </ul>
</p>
</html>"""

  def setCurrentSegmentTransparent(self):
    pass

  def restorePreviewedSegmentTransparency(self):
    pass

  def preview(self):
    opacity = 0.1 + (0.4 * self.previewState / self.previewSteps)
    min = self.scriptedEffect.doubleParameter("MinimumThreshold")
    max = self.scriptedEffect.doubleParameter("MaximumThreshold")

    # Get color of edited segment
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    if not segmentationNode:
      # scene was closed while preview was active
      return
    displayNode = segmentationNode.GetDisplayNode()
    if displayNode is None:
      logging.error("preview: Invalid segmentation display node!")
      color = [0.5,0.5,0.5]
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()

    # Make sure we keep the currently selected segment hidden (the user may have changed selection)
    if segmentID != self.previewedSegmentID:
      self.setCurrentSegmentTransparent()

    r,g,b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()

    # Set values to pipelines
    for sliceWidget in self.previewPipelines:
      pipeline = self.previewPipelines[sliceWidget]
      pipeline.lookupTable.SetTableValue(1,  r, g, b,  opacity)
      layerLogic = self.getMasterVolumeLayerLogic(sliceWidget)
      pipeline.thresholdFilter.SetInputConnection(layerLogic.GetReslice().GetOutputPort())
      pipeline.thresholdFilter.ThresholdBetween(min, max)
      pipeline.actor.VisibilityOn()
      sliceWidget.sliceView().scheduleRender()

    self.previewState += self.previewStep
    if self.previewState >= self.previewSteps:
      self.previewStep = -1
    if self.previewState <= 0:
      self.previewStep = 1

  def getMasterVolumeLayerLogic(self, sliceWidget): # TODO: This function is not a member of SegmentEditorThresholdEffect in 4.10.2, so it is duplicated here for now.
    masterVolumeNode = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    sliceLogic = sliceWidget.sliceLogic()

    backgroundLogic = sliceLogic.GetBackgroundLayer()
    backgroundVolumeNode = backgroundLogic.GetVolumeNode()
    if masterVolumeNode == backgroundVolumeNode:
      return backgroundLogic

    foregroundLogic = sliceLogic.GetForegroundLayer()
    foregroundVolumeNode = foregroundLogic.GetVolumeNode()
    if masterVolumeNode == foregroundVolumeNode:
      return foregroundLogic

    logging.warning("Master volume is not set as either the foreground or background")

    foregroundOpacity = 0.0
    if foregroundVolumeNode:
      compositeNode = sliceLogic.GetSliceCompositeNode()
      foregroundOpacity = compositeNode.GetForegroundOpacity()

    if foregroundOpacity > 0.5:
        return foregroundLogic

    return backgroundLogic

  def setupOptionsFrame(self):
    SegmentEditorThresholdEffect.setupOptionsFrame(self)

    # Hide threshold options
    self.applyButton.setHidden(True)
    self.useForPaintButton.setHidden(True)

    # Add feature options
    self.minimumMinimumFeatureSize = slicer.qMRMLSpinBox()
    self.minimumMinimumFeatureSize.setMRMLScene(slicer.mrmlScene)
    self.minimumMinimumFeatureSize.quantity = "length"
    self.minimumMinimumFeatureSize.value = 3.0
    self.minimumMinimumFeatureSize.singleStep = 0.5
    self.kernelSizePixel = qt.QLabel()
    self.kernelSizePixel.setToolTip("Minimum size of features in pixels. Computed from the segment's spacing and the specified feature size.")
    featureSizeFrame = qt.QHBoxLayout()
    featureSizeFrame.addWidget(self.minimumMinimumFeatureSize)
    featureSizeFrame.addWidget(self.kernelSizePixel)
    self.featureSizeMmLabel = self.scriptedEffect.addLabeledOptionsWidget("Feature size:", featureSizeFrame)
    self.scriptedEffect.addOptionsWidget(featureSizeFrame)

    # Add algorithm options
    self.segmentationAlgorithmSelector = qt.QComboBox()
    self.segmentationAlgorithmSelector.addItem(SEGMENTATION_ALGORITHM_MASKING)
    self.segmentationAlgorithmSelector.addItem(SEGMENTATION_ALGORITHM_GROWCUT)
    self.segmentationAlgorithmSelector.addItem(SEGMENTATION_ALGORITHM_WATERSHED)
    self.scriptedEffect.addLabeledOptionsWidget("Segmentation algorithm: ", self.segmentationAlgorithmSelector)

    # Add ROI options
    self.roiSelector = slicer.qMRMLNodeComboBox()
    self.roiSelector.nodeTypes = ['vtkMRMLAnnotationROINode']
    self.roiSelector.noneEnabled = True
    self.roiSelector.setMRMLScene(slicer.mrmlScene)
    self.scriptedEffect.addLabeledOptionsWidget("ROI: ", self.roiSelector)

    # Connections
    self.minimumMinimumFeatureSize.connect("valueChanged(double)", self.updateMRMLFromGUI)
    self.segmentationAlgorithmSelector.connect("currentIndexChanged(int)", self.updateMRMLFromGUI)

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault(MINIMUM_FEATURE_MM_PARAMETER_NAME, 3)
    self.scriptedEffect.setParameterDefault(SEGMENTATION_ALGORITHM_PARAMETER_NAME, SEGMENTATION_ALGORITHM_MASKING)
    if slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11:
      self.scriptedEffect.setParameterDefault(HISTOGRAM_BRUSH_TYPE_PARAMETER_NAME, HISTOGRAM_BRUSH_TYPE_DRAW)
    SegmentEditorThresholdEffect.setMRMLDefaults(self)

  def updateGUIFromMRML(self):
    SegmentEditorThresholdEffect.updateGUIFromMRML(self)

    featureSizeMm = self.scriptedEffect.doubleParameter(MINIMUM_FEATURE_MM_PARAMETER_NAME)
    wasBlocked = self.minimumMinimumFeatureSize.blockSignals(True)
    self.minimumMinimumFeatureSize.value = abs(featureSizeMm)
    self.minimumMinimumFeatureSize.blockSignals(wasBlocked)

    segmentationAlgorithm = self.scriptedEffect.parameter(SEGMENTATION_ALGORITHM_PARAMETER_NAME)
    wasBlocked = self.segmentationAlgorithmSelector.blockSignals(True)
    self.segmentationAlgorithmSelector.setCurrentText(segmentationAlgorithm)
    self.segmentationAlgorithmSelector.blockSignals(wasBlocked)

    kernelSizePixel = self.getKernelSizePixel()

    if kernelSizePixel[0]<=0 and kernelSizePixel[1]<=0 and kernelSizePixel[2]<=0:
      self.kernelSizePixel.text = "feature too small"
      self.applyButton.setEnabled(False)
    else:
      self.kernelSizePixel.text = "{0}x{1}x{2} pixels".format(abs(kernelSizePixel[0]), abs(kernelSizePixel[1]), abs(kernelSizePixel[2]))
      self.applyButton.setEnabled(True)


  def updateMRMLFromGUI(self):
    SegmentEditorThresholdEffect.updateMRMLFromGUI(self)
    featureSizeMm = self.minimumMinimumFeatureSize.value
    self.scriptedEffect.setParameter(MINIMUM_FEATURE_MM_PARAMETER_NAME, featureSizeMm)

    segmentationAlgorithm = self.segmentationAlgorithmSelector.currentText
    self.scriptedEffect.setParameter(SEGMENTATION_ALGORITHM_PARAMETER_NAME, segmentationAlgorithm)

  def processInteractionEvents(self, callerInteractor, eventId, viewWidget):
    abortEvent = False

    if not callerInteractor.GetControlKey():
      return SegmentEditorThresholdEffect.processInteractionEvents(self, callerInteractor, eventId, viewWidget)

    if eventId == vtk.vtkCommand.LeftButtonPressEvent:
      abortEvent = True

      masterImageData = self.scriptedEffect.masterVolumeImageData()

      xy = callerInteractor.GetEventPosition()
      ijk = self.xyToIjk(xy, viewWidget, masterImageData)

      ijkPoints = vtk.vtkPoints() # TODO: Could get points from all of preview
      origin = masterImageData.GetOrigin()
      spacing = masterImageData.GetSpacing()
      ijkPoints.InsertNextPoint(origin[0]+ijk[0]*spacing[0], origin[1]+ijk[1]*spacing[1], origin[2]+ijk[2]*spacing[2])
      self.apply(ijkPoints)

    return abortEvent

  def runMasking(self, ijkPoints, seedLabelmap, outputLabelmap):
    kernelSizePixel = self.getKernelSizePixel()

    self.floodFillingFilterIsland = vtk.vtkImageThresholdConnectivity()
    self.floodFillingFilterIsland.SetInputData(seedLabelmap)
    self.floodFillingFilterIsland.SetInValue(BACKGROUND_VALUE)
    self.floodFillingFilterIsland.ReplaceInOn()
    self.floodFillingFilterIsland.ReplaceOutOff()
    self.floodFillingFilterIsland.ThresholdBetween(LABEL_VALUE, LABEL_VALUE)
    self.floodFillingFilterIsland.SetSeedPoints(ijkPoints)

    self.dilate = vtk.vtkImageDilateErode3D()
    self.dilate.SetInputConnection(self.floodFillingFilterIsland .GetOutputPort())
    self.dilate.SetDilateValue(LABEL_VALUE)
    self.dilate.SetErodeValue(BACKGROUND_VALUE)
    self.dilate.SetKernelSize(
      2*kernelSizePixel[0]-1,
      2*kernelSizePixel[1]-1,
      2*kernelSizePixel[2]-1)
    self.dilate.Update()

    self.imageMask = vtk.vtkImageMask()
    self.imageMask.SetInputConnection(self.thresh.GetOutputPort())
    self.imageMask.SetMaskedOutputValue(BACKGROUND_VALUE)
    self.imageMask.NotMaskOn()
    self.imageMask.SetMaskInputData(self.dilate.GetOutput())

    self.floodFillingFilter = vtk.vtkImageThresholdConnectivity()
    self.floodFillingFilter.SetInputConnection(self.imageMask.GetOutputPort())
    self.floodFillingFilter.SetInValue(LABEL_VALUE)
    self.floodFillingFilter.SetOutValue(BACKGROUND_VALUE)
    self.floodFillingFilter.ThresholdBetween(LABEL_VALUE, LABEL_VALUE)
    self.floodFillingFilter.SetSeedPoints(ijkPoints)
    self.floodFillingFilter.Update()
    outputLabelmap.ShallowCopy(self.floodFillingFilter.GetOutput())

  def runGrowCut(self, masterImageData, seedLabelmap, outputLabelmap):

    self.clippedMaskImageData = slicer.vtkOrientedImageData()
    intensityBasedMasking = self.scriptedEffect.parameterSetNode().GetMasterVolumeIntensityMask()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    success = segmentationNode.GenerateEditMask(self.clippedMaskImageData,
      self.scriptedEffect.parameterSetNode().GetMaskMode(),
      masterImageData, # reference geometry
      "", # edited segment ID
      self.scriptedEffect.parameterSetNode().GetMaskSegmentID() if self.scriptedEffect.parameterSetNode().GetMaskSegmentID() else "",
      masterImageData if intensityBasedMasking else None,
      self.scriptedEffect.parameterSetNode().GetMasterVolumeIntensityMaskRange() if intensityBasedMasking else None)

    import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic
    self.growCutFilter = vtkSlicerSegmentationsModuleLogic.vtkImageGrowCutSegment()
    self.growCutFilter.SetIntensityVolume(masterImageData)
    self.growCutFilter.SetSeedLabelVolume(seedLabelmap)
    self.growCutFilter.SetMaskVolume(self.clippedMaskImageData)
    self.growCutFilter.Update()
    outputLabelmap.ShallowCopy(self.growCutFilter.GetOutput())

  def runWatershed(self, masterImageData, seedLabelmap, outputLabelmap):

    masterVolumeNode = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(masterVolumeNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(masterImageData, masterVolumeNode)

    seedLabelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
    slicer.mrmlScene.AddNode(seedLabelmapNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(seedLabelmap, seedLabelmapNode)

    # Read input data from Slicer into SimpleITK
    labelImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(seedLabelmapNode.GetName()))
    backgroundImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(masterVolumeNode.GetName()))
    # Run watershed filter
    featureImage = sitk.GradientMagnitudeRecursiveGaussian(backgroundImage, float(self.scriptedEffect.doubleParameter(MINIMUM_FEATURE_MM_PARAMETER_NAME)))
    del backgroundImage
    f = sitk.MorphologicalWatershedFromMarkersImageFilter()
    f.SetMarkWatershedLine(False)
    f.SetFullyConnected(False)
    labelImage = f.Execute(featureImage, labelImage)
    del featureImage
    # Pixel type of watershed output is the same as the input. Convert it to int16 now.
    if labelImage.GetPixelID() != sitk.sitkInt16:
      labelImage = sitk.Cast(labelImage, sitk.sitkInt16)
    # Write result from SimpleITK to Slicer. This currently performs a deep copy of the bulk data.
    sitk.WriteImage(labelImage, sitkUtils.GetSlicerITKReadWriteAddress(seedLabelmapNode.GetName()))

    # Update segmentation from labelmap node and remove temporary nodes
    outputLabelmap.ShallowCopy(seedLabelmapNode.GetImageData())
    outputLabelmap.SetExtent(masterImageData.GetExtent())

    slicer.mrmlScene.RemoveNode(masterVolumeNode)
    slicer.mrmlScene.RemoveNode(seedLabelmapNode)

  def apply(self, ijkPoints):
    kernelSizePixel = self.getKernelSizePixel()
    if kernelSizePixel[0]<=0 and kernelSizePixel[1]<=0 and kernelSizePixel[2]<=0:
      return

    # Get parameter set node
    parameterSetNode = self.scriptedEffect.parameterSetNode()

    # Get parameters
    minimumThreshold = self.scriptedEffect.doubleParameter("MinimumThreshold")
    maximumThreshold = self.scriptedEffect.doubleParameter("MaximumThreshold")

    # Get modifier labelmap
    modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()

    # Get master volume image data
    masterImageData = self.scriptedEffect.masterVolumeImageData()

    # Set intensity range
    oldMasterVolumeIntensityMask = parameterSetNode.GetMasterVolumeIntensityMask()
    parameterSetNode.MasterVolumeIntensityMaskOn()
    oldIntensityMaskRange = parameterSetNode.GetMasterVolumeIntensityMaskRange()
    intensityRange = [minimumThreshold, maximumThreshold]
    if oldMasterVolumeIntensityMask:
      intensityRange = [max(oldIntensityMaskRange[0], minimumThreshold), min(oldIntensityMaskRange[1], maximumThreshold)]
    parameterSetNode.SetMasterVolumeIntensityMaskRange(intensityRange)

    roiNode = self.roiSelector.currentNode()
    clippedMasterImageData = masterImageData
    if roiNode is not None:
      worldToImageMatrix = vtk.vtkMatrix4x4()
      masterImageData.GetWorldToImageMatrix(worldToImageMatrix)
    
      bounds = [0,0,0,0,0,0]
      roiNode.GetRASBounds(bounds)
      corner1RAS = [bounds[0], bounds[2], bounds[4], 1]
      corner1IJK = [0, 0, 0, 0]
      worldToImageMatrix.MultiplyPoint(corner1RAS, corner1IJK)
    
      corner2RAS = [bounds[1], bounds[3], bounds[5], 1]
      corner2IJK = [0, 0, 0, 0]
      worldToImageMatrix.MultiplyPoint(corner2RAS, corner2IJK)
    
      extent = [0, -1, 0, -1, 0, -1]
      for i in range(3):
          lowerPoint = min(corner1IJK[i], corner2IJK[i])
          upperPoint = max(corner1IJK[i], corner2IJK[i])
          extent[2*i] = int(math.floor(lowerPoint))
          extent[2*i+1] = int(math.ceil(upperPoint))

      imageToWorldMatrix = vtk.vtkMatrix4x4()
      masterImageData.GetImageToWorldMatrix(imageToWorldMatrix)
      clippedMasterImageData = slicer.vtkOrientedImageData()
      self.padder = vtk.vtkImageConstantPad()
      self.padder.SetInputData(masterImageData)
      self.padder.SetOutputWholeExtent(extent)
      self.padder.Update()
      clippedMasterImageData.ShallowCopy(self.padder.GetOutput())
      clippedMasterImageData.SetImageToWorldMatrix(imageToWorldMatrix)

    # Pipeline
    self.thresh = vtk.vtkImageThreshold()
    self.thresh.SetInValue(LABEL_VALUE)
    self.thresh.SetOutValue(BACKGROUND_VALUE)
    self.thresh.SetInputData(clippedMasterImageData)
    self.thresh.ThresholdBetween(minimumThreshold, maximumThreshold)
    self.thresh.SetOutputScalarTypeToUnsignedChar()
    self.thresh.Update()

    self.erode = vtk.vtkImageDilateErode3D()
    self.erode.SetInputConnection(self.thresh.GetOutputPort())
    self.erode.SetDilateValue(BACKGROUND_VALUE)
    self.erode.SetErodeValue(LABEL_VALUE)
    self.erode.SetKernelSize(
      kernelSizePixel[0],
      kernelSizePixel[1],
      kernelSizePixel[2])

    self.erodeCast = vtk.vtkImageCast()
    self.erodeCast.SetInputConnection(self.erode.GetOutputPort())
    self.erodeCast.SetOutputScalarTypeToUnsignedInt()
    self.erodeCast.Update()

    # Remove small islands
    self.islandMath = vtkITK.vtkITKIslandMath()
    self.islandMath.SetInputConnection(self.erodeCast.GetOutputPort())
    self.islandMath.SetFullyConnected(False)
    self.islandMath.SetMinimumSize(10) #TODO: Why X voxels?

    self.islandThreshold = vtk.vtkImageThreshold()
    self.islandThreshold.SetInputConnection(self.islandMath.GetOutputPort())
    self.islandThreshold.ThresholdByLower(BACKGROUND_VALUE)
    self.islandThreshold.SetInValue(BACKGROUND_VALUE)
    self.islandThreshold.SetOutValue(LABEL_VALUE)
    self.islandThreshold.SetOutputScalarTypeToUnsignedChar()
    self.islandThreshold.Update()

    segmentationAlgorithm = self.scriptedEffect.parameter(SEGMENTATION_ALGORITHM_PARAMETER_NAME)
    if segmentationAlgorithm == SEGMENTATION_ALGORITHM_MASKING:
      self.runMasking(ijkPoints, self.islandThreshold.GetOutput(), modifierLabelmap)

    else:
      self.floodFillingFilterIsland = vtk.vtkImageThresholdConnectivity()
      self.floodFillingFilterIsland.SetInputConnection(self.islandThreshold.GetOutputPort())
      self.floodFillingFilterIsland.SetInValue(SELECTED_ISLAND_VALUE)
      self.floodFillingFilterIsland.ReplaceInOn()
      self.floodFillingFilterIsland.ReplaceOutOff()
      self.floodFillingFilterIsland.ThresholdBetween(LABEL_VALUE, LABEL_VALUE)
      self.floodFillingFilterIsland.SetSeedPoints(ijkPoints)
      self.floodFillingFilterIsland.Update()

      self.maskCast = vtk.vtkImageCast()
      self.maskCast.SetInputData(self.thresh.GetOutput())
      self.maskCast.SetOutputScalarTypeToUnsignedChar()
      self.maskCast.Update()

      self.imageMask = vtk.vtkImageMask()
      self.imageMask.SetInputConnection(self.floodFillingFilterIsland.GetOutputPort())
      self.imageMask.SetMaskedOutputValue(OUTSIDE_THRESHOLD_VALUE)
      self.imageMask.SetMaskInputData(self.maskCast.GetOutput())
      self.imageMask.Update()

      imageMaskOutput = slicer.vtkOrientedImageData()
      imageMaskOutput.ShallowCopy(self.imageMask.GetOutput())
      imageMaskOutput.CopyDirections(clippedMasterImageData)

      imageToWorldMatrix = vtk.vtkMatrix4x4()
      imageMaskOutput.GetImageToWorldMatrix(imageToWorldMatrix)

      segmentOutputLabelmap = slicer.vtkOrientedImageData()
      if segmentationAlgorithm == SEGMENTATION_ALGORITHM_GROWCUT:
        self.runGrowCut(clippedMasterImageData, imageMaskOutput, segmentOutputLabelmap)
      elif segmentationAlgorithm == SEGMENTATION_ALGORITHM_WATERSHED:
        self.runWatershed(clippedMasterImageData, imageMaskOutput, segmentOutputLabelmap)
      else:
        logging.error("Unknown segmentation algorithm: \"" + segmentationAlgorithm + "\"")

      segmentOutputLabelmap.SetImageToWorldMatrix(imageToWorldMatrix)

      self.selectedSegmentThreshold = vtk.vtkImageThreshold()
      self.selectedSegmentThreshold.SetInputData(segmentOutputLabelmap)
      self.selectedSegmentThreshold.ThresholdBetween(SELECTED_ISLAND_VALUE, SELECTED_ISLAND_VALUE)
      self.selectedSegmentThreshold.SetInValue(LABEL_VALUE)
      self.selectedSegmentThreshold.SetOutValue(BACKGROUND_VALUE)
      self.selectedSegmentThreshold.SetOutputScalarType(modifierLabelmap.GetScalarType())
      self.selectedSegmentThreshold.Update()
      modifierLabelmap.ShallowCopy(self.selectedSegmentThreshold.GetOutput())

    self.scriptedEffect.saveStateForUndo()
    self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd)

    parameterSetNode.SetMasterVolumeIntensityMask(oldMasterVolumeIntensityMask)
    parameterSetNode.SetMasterVolumeIntensityMaskRange(oldIntensityMaskRange)

  def getKernelSizePixel(self):
    selectedSegmentLabelmapSpacing = [1.0, 1.0, 1.0]
    selectedSegmentLabelmap = self.scriptedEffect.selectedSegmentLabelmap()
    if selectedSegmentLabelmap:
      selectedSegmentLabelmapSpacing = selectedSegmentLabelmap.GetSpacing()

    # size rounded to nearest odd number. If kernel size is even then image gets shifted.
    featureSizeMm = abs(self.scriptedEffect.doubleParameter(MINIMUM_FEATURE_MM_PARAMETER_NAME))
    kernelSizePixel = [int(round((featureSizeMm / selectedSegmentLabelmapSpacing[componentIndex]+1)/2)*2-1) for componentIndex in range(3)]
    return kernelSizePixel

MINIMUM_FEATURE_MM_PARAMETER_NAME = "MinimumFeatureSizeMm"
SEGMENTATION_ALGORITHM_PARAMETER_NAME = "SegmentationAlgorithm"
SEGMENTATION_ALGORITHM_MASKING = "Masking"
SEGMENTATION_ALGORITHM_GROWCUT = "GrowCut"
SEGMENTATION_ALGORITHM_WATERSHED = "WaterShed"

BACKGROUND_VALUE = 0
LABEL_VALUE = 1
SELECTED_ISLAND_VALUE = 2
OUTSIDE_THRESHOLD_VALUE = 3
