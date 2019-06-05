# This is a complete example that computes histogram for each region of a volume defined by a segment.
# This script requires installation of  SegmentEditorExtraEffects extension, as it uses Crop segment effect,
# which is provided by this extension.
 
import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *
import vtkSegmentationCorePython as vtkSegmentationCore 
import sitkUtils
import SimpleITK as sitk

 
class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses a currently existing segment to crop the master volume with a chosen voxel fill value."""
 
  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Crop segment'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)
 
    #Effect-specific members
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
    return """<html>Create a volume node for each segment, cropped to the segment extent. Cropping is applied to the master volume by default. Optionally, padding can be added to the output volumes.<p>
</html>"""
 
  def setupOptionsFrame(self):
     
    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = True
    self.inputVolumeSelector.addEnabled = True
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.noneEnabled = True
    self.inputVolumeSelector.noneDisplay = "(Master volume)"
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.inputVolumeSelector.setToolTip("Volume to crop. Default is current master volume node.")
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputVolumeChanged)
 
    inputLayout = qt.QHBoxLayout()
    inputLayout.addWidget(self.inputVolumeSelector)
    self.scriptedEffect.addLabeledOptionsWidget("Input Volume: ", inputLayout)
     
    # Pad size
    self.pad = qt.QSpinBox()
    self.pad.setToolTip("Choose the number of voxels used to pad the image in each dimension")
    self.pad.minimum = 0
    self.pad.maximum = 1000
    self.pad.connect("valueChanged(int)", self.onVoxelPadValueChanged)
    self.padLabel = qt.QLabel("Pad voxels: ")
     
    self.padPercent = qt.QDoubleSpinBox()
    self.padPercent.setToolTip("Choose size of the padding in each dimension as a percent of the original image size")
    self.padPercent.minimum = 0
    self.padPercent.maximum = 100
    self.padPercent.connect("valueChanged(double)", self.onVoxelPadPercentChanged)
    self.padPercentLabel = qt.QLabel("Pad percentage: ")

    # Fill value layouts
    # addWidget(*Widget, row, column, rowspan, colspan)
    padValueLayout = qt.QGridLayout()
    padValueLayout.addWidget(self.padLabel,1,1,1,1)
    padValueLayout.addWidget(self.pad,1,2,1,1)
    padValueLayout.addWidget(self.padPercentLabel,1,3,1,1)
    padValueLayout.addWidget(self.padPercent,1,4,1,1)

    self.scriptedEffect.addOptionsWidget(padValueLayout)
    
    self.fillValue = qt.QSpinBox()
    self.fillValue.setToolTip("Choose the voxel intensity that will be used to pad the output volumes.")
    self.fillValue.minimum = -32768
    self.fillValue.maximum = 65535
    self.fillValue.value=0
    self.fillValueLabel = qt.QLabel("Fill value: ")
    
    fillValueLayout = qt.QFormLayout()
    fillValueLayout.addRow(self.fillValueLabel, self.fillValue)
    self.scriptedEffect.addOptionsWidget(fillValueLayout)     
    
    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Generate volumes for each segment, cropped to the segment extent. No undo operation available once applied.")
    self.scriptedEffect.addOptionsWidget(self.applyButton)
    self.applyButton.connect('clicked()', self.onApply)
 
  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor
   
  def onVoxelPadValueChanged(self):
    #reset percentage boxes to match voxel number
    dimension = self.getInputVolume().GetImageData().GetDimensions() 
    newPadValue = float(self.pad.value)/dimension[0]*100
    if(abs(newPadValue-self.padPercent.value) > 1):
      self.padPercent.setValue( round(newPadValue,2) )
    
  def onVoxelPadPercentChanged(self):
    #reset voxel boxes to match percents
    dimension = self.getInputVolume().GetImageData().GetDimensions() 
    newPadPercent = float(self.padPercent.value)/100*dimension[0]
    if(abs(newPadPercent-self.pad.value) > 1):
      self.pad.setValue( round(newPadPercent) )
     
  def updateGUIFromMRML(self):
    inputVolume = self.inputVolumeSelector.currentNode()
    if inputVolume is None:
      inputVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    masterVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
 
  def getInputVolume(self):
    inputVolume = self.inputVolumeSelector.currentNode()
    if inputVolume is None:
      inputVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    return inputVolume

  def onInputVolumeChanged(self):
    self.updateGUIFromMRML()
  
  def onApply(self):
    inputVolume = self.getInputVolume()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    volumesLogic = slicer.modules.volumes.logic()
    scene = inputVolume.GetScene()
    padExtent = [-self.pad.value, self.pad.value, -self.pad.value, self.pad.value, -self.pad.value, self.pad.value]
    #iterate over segments
    for segmentIndex in range(segmentationNode.GetSegmentation().GetNumberOfSegments()):
      segmentID = segmentationNode.GetSegmentation().GetNthSegmentID(segmentIndex)
      segmentIDs = vtk.vtkStringArray()
      segmentIDs.InsertNextValue(segmentID)
      
      # create volume for output
      outputVolumeName = inputVolume.GetName() + '_' + segmentID
      outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)
      
      # crop segment
      slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
      import SegmentEditorMaskVolumeLib
      SegmentEditorMaskVolumeLib.SegmentEditorEffect.maskVolumeWithSegment(self,segmentationNode, segmentID, "FILL_OUTSIDE", [0], inputVolume, outputVolume)
      
      #calculate extent of masked image
      cropThreshold = 0
      img = slicer.modules.segmentations.logic().CreateOrientedImageDataFromVolumeNode(outputVolume) 
      img.UnRegister(None) 
      extent=[0,0,0,0,0,0]
      vtkSegmentationCore.vtkOrientedImageDataResample.CalculateEffectiveExtent(img, extent, cropThreshold) 

      # pad and crop
      cropFilter = vtk.vtkImageConstantPad()
      cropFilter.SetInputData(outputVolume.GetImageData())
      cropFilter.SetConstant(self.fillValue.value)   
      cropFilter.SetOutputWholeExtent(extent)
      cropFilter.Update()
      
      padFilter = vtk.vtkImageConstantPad()
      padFilter.SetInputData(cropFilter.GetOutput())
      padFilter.SetConstant(self.fillValue.value)
      for i in range(len(extent)):
        extent[i]=extent[i]+padExtent[i]
           
      padFilter.SetOutputWholeExtent(extent)
      padFilter.Update()
      outputVolume.SetAndObserveImageData(padFilter.GetOutput())
      
      qt.QApplication.restoreOverrideCursor()
  
  
