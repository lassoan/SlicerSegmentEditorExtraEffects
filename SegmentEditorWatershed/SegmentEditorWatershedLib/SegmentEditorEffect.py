import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorAutoCompleteEffect):
  """This effect uses Watershed algorithm to partition the input volume"""

  def __init__(self, scriptedEffect):
    AbstractScriptedSegmentEditorAutoCompleteEffect.__init__(self, scriptedEffect)
    scriptedEffect.name = 'Watershed'
    self.minimumNumberOfSegments = 2
    self.clippedMasterImageDataRequired = True # source volume intensities are used by this effect
    self.growCutFilter = None

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
    return """<html>Growing segments to create complete segmentation<br>.
Location, size, and shape of initial segments and content of source volume are taken into account.
Final segment boundaries will be placed where source volume brightness changes abruptly. Instructions:<p>
<ul style="margin: 0">
<li>Use Paint or other offects to draw seeds in each region that should belong to a separate segment.
Paint each seed with a different segment. Minimum two segments are required.</li>
<li>Click <dfn>Initialize</dfn> to compute preview of full segmentation.</li>
<li>Browse through image slices. If previewed segmentation result is not correct then switch to
Paint or other effects and add more seeds in the misclassified region. Full segmentation will be
updated automatically within a few seconds</li>
<li>Click <dfn>Apply</dfn> to update segmentation with the previewed result.</li>
</ul><p>
The effect is different from the Grow from seeds effect in that smoothness of structures can be defined, which can prevent leakage.<p>
Masking settings are bypassed. If segments overlap, segment higher in the segments table will have priority.
The effect uses <a href="https://itk.org/Doxygen/html/classitk_1_1MorphologicalWatershedFromMarkersImageFilter.html">watershed method</a>.
<p></html>"""

  def reset(self):
    self.growCutFilter = None
    AbstractScriptedSegmentEditorAutoCompleteEffect.reset(self)
    self.updateGUIFromMRML()

  def setupOptionsFrame(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.setupOptionsFrame(self)

     # Object scale slider
    self.objectScaleMmSlider = slicer.qMRMLSliderWidget()
    self.objectScaleMmSlider.setMRMLScene(slicer.mrmlScene)
    self.objectScaleMmSlider.quantity = "length" # get unit, precision, etc. from MRML unit node
    self.objectScaleMmSlider.minimum = 0.0001  # object scale of 0 would throw an exception when calling sitk.GradientMagnitudeRecursiveGaussian
    self.objectScaleMmSlider.maximum = 10
    self.objectScaleMmSlider.value = 2.0
    self.objectScaleMmSlider.setToolTip('Increasing this value smooths the segmentation and reduces leaks. This is the sigma used for edge detection.')
    self.scriptedEffect.addLabeledOptionsWidget("Object scale:", self.objectScaleMmSlider)
    self.objectScaleMmSlider.connect('valueChanged(double)', self.updateAlgorithmParameterFromGUI)

  def setMRMLDefaults(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.setMRMLDefaults(self)
    self.scriptedEffect.setParameterDefault("ObjectScaleMm", 2.0)

  def updateGUIFromMRML(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.updateGUIFromMRML(self)
    objectScaleMm = self.scriptedEffect.doubleParameter("ObjectScaleMm")
    wasBlocked = self.objectScaleMmSlider.blockSignals(True)
    self.objectScaleMmSlider.value = abs(objectScaleMm)
    self.objectScaleMmSlider.blockSignals(wasBlocked)

  def updateMRMLFromGUI(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.updateMRMLFromGUI(self)
    self.scriptedEffect.setParameter("ObjectScaleMm", self.objectScaleMmSlider.value)

  def updateAlgorithmParameterFromGUI(self):
    self.updateMRMLFromGUI()

    # Trigger preview update
    if self.getPreviewNode():
      self.delayedAutoUpdateTimer.start()

  def computePreviewLabelmap(self, mergedImage, outputLabelmap):

    import vtkSegmentationCorePython as vtkSegmentationCore
    import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

    sourceVolumeNode = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(sourceVolumeNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(self.clippedMasterImageData, sourceVolumeNode)

    mergedLabelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
    slicer.mrmlScene.AddNode(mergedLabelmapNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(mergedImage, mergedLabelmapNode)

    outputRasToIjk = vtk.vtkMatrix4x4()
    mergedImage.GetImageToWorldMatrix(outputRasToIjk)
    outputExtent = mergedImage.GetExtent()

    # Run segmentation algorithm
    import SimpleITK as sitk
    import sitkUtils
    # Read input data from Slicer into SimpleITK
    labelImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(mergedLabelmapNode.GetName()))
    backgroundImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(sourceVolumeNode.GetName()))
    # Run watershed filter
    featureImage = sitk.GradientMagnitudeRecursiveGaussian(backgroundImage, float(self.scriptedEffect.doubleParameter("ObjectScaleMm")))
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
    sitk.WriteImage(labelImage, sitkUtils.GetSlicerITKReadWriteAddress(mergedLabelmapNode.GetName()))

    # Update segmentation from labelmap node and remove temporary nodes
    outputLabelmap.ShallowCopy(mergedLabelmapNode.GetImageData())
    outputLabelmap.SetImageToWorldMatrix(outputRasToIjk)
    outputLabelmap.SetExtent(outputExtent)

    slicer.mrmlScene.RemoveNode(sourceVolumeNode)
    slicer.mrmlScene.RemoveNode(mergedLabelmapNode)

    qt.QApplication.restoreOverrideCursor()
