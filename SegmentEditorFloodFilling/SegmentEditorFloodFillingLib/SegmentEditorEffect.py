import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect fills a region enclosed in a segment at clicked position"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Flood filling'
    scriptedEffect.perSegment = False # this effect operates on all segments at once (not on a single selected segment)
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)
    self.clippedMasterImageData = None
    self.lastRoiNodeId = ""
    self.lastRoiNodeModifiedTime = 0

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
    return """Fill connected voxels with similar intensity\n.
Click in the image to add voxels that have similar intensity to the clicked voxel.
Masking settings can be used to restrict growing to a specific region.
"""

  def activate(self):
    # Update intensity range
    self.masterVolumeNodeChanged()

  def setupOptionsFrame(self):

    self.intensityToleranceSlider = ctk.ctkSliderWidget()
    self.intensityToleranceSlider.setToolTip("Tolerance.")
    self.intensityToleranceSlider.minimum = 0.01
    self.intensityToleranceSlider.maximum = 1000.0
    self.intensityToleranceSlider.value = 10
    self.intensityToleranceSlider.singleStep = 1.0
    self.intensityToleranceSlider.pageStep = 5.0
    self.intensityToleranceLabel = self.scriptedEffect.addLabeledOptionsWidget("Intensity tolerance:", self.intensityToleranceSlider)

    self.neighborhoodSizeMmSlider = ctk.ctkSliderWidget()
    self.neighborhoodSizeMmSlider.setToolTip("Regions are added only if all voxels in the neighborhood have similar intensities."
      "Use higher values prevent leakage. Use lower values to allow capturing finer details.")
    self.neighborhoodSizeMmSlider.minimum = 0.0
    self.neighborhoodSizeMmSlider.maximum = 30.0
    self.neighborhoodSizeMmSlider.value = 1.0
    self.neighborhoodSizeMmSlider.singleStep = 0.01
    self.neighborhoodSizeMmSlider.pageStep = 0.5
    self.neighborhoodSizeLabel = self.scriptedEffect.addLabeledOptionsWidget("Neighborhood size:", self.neighborhoodSizeMmSlider)

    self.neighborhoodSizeMmSlider.connect("valueChanged(double)", self.updateMRMLFromGUI)
    self.intensityToleranceSlider.connect("valueChanged(double)", self.updateMRMLFromGUI)

    # Add ROI options
    self.roiSelector = slicer.qMRMLNodeComboBox()
    self.roiSelector.nodeTypes = ['vtkMRMLMarkupsROINode', 'vtkMRMLAnnotationROINode']
    self.roiSelector.noneEnabled = True
    self.roiSelector.setMRMLScene(slicer.mrmlScene)
    self.scriptedEffect.addLabeledOptionsWidget("ROI: ", self.roiSelector)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    #return slicer.util.mainWindow().cursor
    return qt.QCursor(qt.Qt.PointingHandCursor)

  def masterVolumeNodeChanged(self):
    # Force recomputation of clipped master image data
    self.clippedMasterImageData = None

    # Set scalar range of master volume image data to threshold slider
    import math
    import vtkSegmentationCorePython as vtkSegmentationCore
    masterImageData = self.scriptedEffect.masterVolumeImageData()
    if not masterImageData:
      return

    # TODO: it might be useful to add a convenience function, which determines size and intensity min/max/step/decimals
    # based on the selected master volume's size, spacing, and intensity range

    # Intensity slider
    lo, hi = masterImageData.GetScalarRange()
    if (hi-lo > 0):
      range = hi-lo
      stepSize = 1

      # For floating-point volume: step size is 1/1000th of range (but maximum 1)
      if masterImageData.GetScalarType() == vtk.VTK_FLOAT or masterImageData.GetScalarType() == vtk.VTK_DOUBLE:
        stepSize = 10**(math.floor(math.log(range/1000.0)/math.log(10)))
        if stepSize > 1:
          stepSize = 1

      self.intensityToleranceSlider.decimals = math.log(stepSize)/math.log(10)
      self.intensityToleranceSlider.minimum = stepSize
      self.intensityToleranceSlider.maximum = range
      self.intensityToleranceSlider.singleStep = stepSize
      self.intensityToleranceSlider.pageStep = stepSize*10

    # Size slider
    minSpacing = min(masterImageData.GetSpacing())
    self.neighborhoodSizeMmSlider.maximum = 10**(math.ceil(math.log(minSpacing*100.0)/math.log(10)))
    self.neighborhoodSizeMmSlider.singleStep = self.neighborhoodSizeMmSlider.minimum
    self.neighborhoodSizeMmSlider.pageStep = self.neighborhoodSizeMmSlider.singleStep*10

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("IntensityTolerance", 10.0)
    self.scriptedEffect.setParameterDefault("NeighborhoodSizeMm", 1.0)

  def updateGUIFromMRML(self):
    self.intensityToleranceSlider.blockSignals(True)
    self.intensityToleranceSlider.value = self.scriptedEffect.doubleParameter("IntensityTolerance")
    self.intensityToleranceSlider.blockSignals(False)
    self.neighborhoodSizeMmSlider.blockSignals(True)
    self.neighborhoodSizeMmSlider.value = self.scriptedEffect.doubleParameter("NeighborhoodSizeMm")
    self.neighborhoodSizeMmSlider.blockSignals(False)

  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("IntensityTolerance", self.intensityToleranceSlider.value)
    self.scriptedEffect.setParameter("NeighborhoodSizeMm", self.neighborhoodSizeMmSlider.value)

  def getClippedMasterImageData(self):
    # Return masterImageData unchanged if there is no ROI
    masterImageData = self.scriptedEffect.masterVolumeImageData()
    roiNode = self.roiSelector.currentNode()
    if roiNode is None or masterImageData is None:
      self.clippedMasterImageData = None
      self.lastRoiNodeId = ""
      self.lastRoiNodeModifiedTime = 0
      return masterImageData

    # Return last clipped image data if there was no change
    if (self.clippedMasterImageData is not None
      and roiNode.GetID() == self.lastRoiNodeId
      and roiNode.GetMTime() == self.lastRoiNodeModifiedTime):
      # Use cached clipped master image data
      return self.clippedMasterImageData

    # Compute clipped master image
    import SegmentEditorLocalThresholdLib
    self.clippedMasterImageData = SegmentEditorLocalThresholdLib.SegmentEditorEffect.cropOrientedImage(masterImageData, roiNode)
    self.lastRoiNodeId = roiNode.GetID()
    self.lastRoiNodeModifiedTime = roiNode.GetMTime()
    return self.clippedMasterImageData

  def processInteractionEvents(self, callerInteractor, eventId, viewWidget):
    abortEvent = False

    # Only allow for slice views
    if viewWidget.className() != "qMRMLSliceWidget":
      return abortEvent

    if eventId == vtk.vtkCommand.LeftButtonPressEvent:
      # This can be a long operation - indicate it to the user
      qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
      try:
        xy = callerInteractor.GetEventPosition()
        import vtkSegmentationCorePython as vtkSegmentationCore
        masterImageData = self.getClippedMasterImageData()
        ijk = self.xyToIjk(xy, viewWidget, masterImageData)
        self.floodFillFromPoint(ijk)
      except IndexError:
        logging.error('apply: Failed to threshold master volume!')
      finally:
        qt.QApplication.restoreOverrideCursor()
      abortEvent = True

    return abortEvent

  def floodFillFromPoint(self, ijk):
    """Fills the segment taking based on the current master volume.
    Input IJK position is voxel coordinates of master volume.
    """
    self.scriptedEffect.saveStateForUndo()

    # Get master volume image data
    import vtkSegmentationCorePython as vtkSegmentationCore
    masterImageData = self.getClippedMasterImageData()
    selectedSegmentLabelmap = self.scriptedEffect.selectedSegmentLabelmap()

    # Get modifier labelmap
    modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()

    pixelValue = masterImageData.GetScalarComponentAsFloat(ijk[0], ijk[1], ijk[2], 0)

    useSegmentationAsStencil = False

    # Perform thresholding
    floodFillingFilter = vtk.vtkImageThresholdConnectivity()
    floodFillingFilter.SetInputData(masterImageData)
    seedPoints = vtk.vtkPoints()
    origin = masterImageData.GetOrigin()
    spacing = masterImageData.GetSpacing()
    seedPoints.InsertNextPoint(origin[0]+ijk[0]*spacing[0], origin[1]+ijk[1]*spacing[1], origin[2]+ijk[2]*spacing[2])
    floodFillingFilter.SetSeedPoints(seedPoints)

    maskImageData = vtkSegmentationCore.vtkOrientedImageData()
    intensityBasedMasking = self.scriptedEffect.parameterSetNode().GetMasterVolumeIntensityMask()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    success = segmentationNode.GenerateEditMask(maskImageData,
      self.scriptedEffect.parameterSetNode().GetMaskMode(),
      masterImageData, # reference geometry
      self.scriptedEffect.parameterSetNode().GetSelectedSegmentID(),
      self.scriptedEffect.parameterSetNode().GetMaskSegmentID() if self.scriptedEffect.parameterSetNode().GetMaskSegmentID() else "",
      masterImageData if intensityBasedMasking else None,
      self.scriptedEffect.parameterSetNode().GetMasterVolumeIntensityMaskRange() if intensityBasedMasking else None)
    if success:
      stencil = vtk.vtkImageToImageStencil()
      stencil.SetInputData(maskImageData)
      stencil.ThresholdByLower(0)
      stencil.Update()
      floodFillingFilter.SetStencilData(stencil.GetOutput())
    else:
      logging.error("Failed to create edit mask")

    neighborhoodSizeMm = self.neighborhoodSizeMmSlider.value
    floodFillingFilter.SetNeighborhoodRadius(neighborhoodSizeMm,neighborhoodSizeMm,neighborhoodSizeMm)
    floodFillingFilter.SetNeighborhoodFraction(0.5)

    if useSegmentationAsStencil:
      stencilFilter = vtk.vtkImageToImageStencil()
      stencilFilter.SetInputData(selectedSegmentLabelmap)
      stencilFilter.ThresholdByLower(0)
      stencilFilter.Update()
      floodFillingFilter.SetStencilData(stencilFilter.GetOutput())

    pixelValueTolerance = float(self.intensityToleranceSlider.value)
    floodFillingFilter.ThresholdBetween(pixelValue-pixelValueTolerance, pixelValue+pixelValueTolerance)

    floodFillingFilter.SetInValue(1)
    floodFillingFilter.SetOutValue(0)
    floodFillingFilter.Update()
    modifierLabelmap.DeepCopy(floodFillingFilter.GetOutput())

    # Apply changes
    self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd)
