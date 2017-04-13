import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses Watershed algorithm to partition the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Flood filling'
    scriptedEffect.perSegment = False # this effect operates on all segments at once (not on a single selected segment)
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
    return """Fill connected voxels with similar intensity\n.
Click in the image to add voxels that have similar intensity to the clicked voxel.
"""

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
    self.neighborhoodSizeMmSlider.minimum = 0.01
    self.neighborhoodSizeMmSlider.maximum = 30.0
    self.neighborhoodSizeMmSlider.value = 1.0
    self.neighborhoodSizeMmSlider.singleStep = 0.01
    self.neighborhoodSizeMmSlider.pageStep = 0.5
    self.neighborhoodSizeLabel = self.scriptedEffect.addLabeledOptionsWidget("Neighborhood size:", self.neighborhoodSizeMmSlider)

    self.neighborhoodSizeMmSlider.connect("valueChanged(double)", self.updateMRMLFromGUI)
    self.intensityToleranceSlider.connect("valueChanged(double)", self.updateMRMLFromGUI)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    #return slicer.util.mainWindow().cursor
    return qt.QCursor(qt.Qt.PointingHandCursor)
    

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

  def processInteractionEvents(self, callerInteractor, eventId, viewWidget):
    abortEvent = False

    # Only allow for slice views
    if viewWidget.className() != "qMRMLSliceWidget":
      return abortEvent

    if eventId == vtk.vtkCommand.LeftButtonPressEvent:
      self.scriptedEffect.saveStateForUndo()

      # Get master volume image data
      import vtkSegmentationCorePython as vtkSegmentationCore
      masterImageData = self.scriptedEffect.masterVolumeImageData()
      selectedSegmentLabelmap = self.scriptedEffect.selectedSegmentLabelmap()

      # Get modifier labelmap
      modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()

      xy = callerInteractor.GetEventPosition()
      ijk = self.xyToIjk(xy, viewWidget, masterImageData)

      pixelValue = masterImageData.GetScalarComponentAsFloat(ijk[0], ijk[1], ijk[2], 0)      
      
      useSegmentationAsStencil = False
      
      try:

        # This can be a long operation - indicate it to the user
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

        # Perform thresholding
        floodFillingFilter = vtk.vtkImageThresholdConnectivity()       
        floodFillingFilter.SetInputData(masterImageData)
        seedPoints = vtk.vtkPoints()
        origin = masterImageData.GetOrigin()
        spacing = masterImageData.GetSpacing()
        seedPoints.InsertNextPoint(origin[0]+ijk[0]*spacing[0], origin[1]+ijk[1]*spacing[1], origin[2]+ijk[2]*spacing[2])
        floodFillingFilter.SetSeedPoints(seedPoints)
        
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
      except IndexError:
        logging.error('apply: Failed to threshold master volume!')
      finally:
        qt.QApplication.restoreOverrideCursor() 

      # Apply changes
      self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd)
      abortEvent = True
        
    return abortEvent
      