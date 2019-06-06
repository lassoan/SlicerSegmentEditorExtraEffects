# This is a complete example that computes histogram for each region of a volume defined by a segment.
# This script requires installation of  SegmentEditorExtraEffects extension, as it uses the Split volume effect,
# which is provided by this extension.
 
import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *
import vtkSegmentationCorePython as vtkSegmentationCore 
import sitkUtils
import SimpleITK as sitk

 
class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect creates a volume for each segment, cropped to the segment extent with optional padding."""
 
  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Split volume'
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
    return """Create a volume node for each segment, cropped to the segment extent.\n
Extent is expanded by the specified number of padding voxels along each axis.
Voxels outside the segment are set to the requested fill value.
Generated volumes are not effected by segmentation undo operation.
</html>"""

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("FillValue", "0")
    self.scriptedEffect.setParameterDefault("PaddingVoxels", "5")

  def updateGUIFromMRML(self):
    wasBlocked = self.fillValueEdit.blockSignals(True)
    try:
      self.fillValueEdit.setValue(int(self.scriptedEffect.parameter("FillValue")))
    except:
      self.fillValueEdit.setValue(0)
    self.fillValueEdit.blockSignals(wasBlocked)

    wasBlocked = self.padEdit.blockSignals(True)
    try:
      self.padEdit.setValue(int(self.scriptedEffect.parameter("PaddingVoxels")))
    except:
      self.padEdit.setValue(5)
    self.padEdit.blockSignals(wasBlocked)
 
  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("FillValue", self.fillValueEdit.value)
    self.scriptedEffect.setParameter("PaddingVoxels", self.padEdit.value)

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
    self.inputVolumeSelector.setToolTip("Volume to split. Default is current master volume node.")
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
 
    inputLayout = qt.QHBoxLayout()
    inputLayout.addWidget(self.inputVolumeSelector)
    self.scriptedEffect.addLabeledOptionsWidget("Input Volume: ", inputLayout)
     
    # Pad size
    self.padEdit = qt.QSpinBox()
    self.padEdit.setToolTip("Choose the number of voxels used to pad the image in each dimension")
    self.padEdit.minimum = 0
    self.padEdit.maximum = 1000
    self.padEdit.connect("valueChanged(int)", self.updateMRMLFromGUI)
    self.padLabel = qt.QLabel("Pad voxels: ")
    
    # Fill value layouts
    # addWidget(*Widget, row, column, rowspan, colspan)
    padValueLayout = qt.QFormLayout()
    padValueLayout.addRow(self.padLabel, self.padEdit)

    self.scriptedEffect.addOptionsWidget(padValueLayout)
    
    self.fillValueEdit = qt.QSpinBox()
    self.fillValueEdit.setToolTip("Choose the voxel intensity that will be used to pad the output volumes.")
    self.fillValueEdit.minimum = -32768
    self.fillValueEdit.maximum = 65535
    self.fillValueEdit.value=0
    self.fillValueEdit.connect("valueChanged(int)", self.updateMRMLFromGUI)
    self.fillValueLabel = qt.QLabel("Fill value: ")
    
    fillValueLayout = qt.QFormLayout()
    fillValueLayout.addRow(self.fillValueLabel, self.fillValueEdit)
    self.scriptedEffect.addOptionsWidget(fillValueLayout)     
    
    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Generate a volume for each visible segment")
    self.scriptedEffect.addOptionsWidget(self.applyButton)
    self.applyButton.connect('clicked()', self.onApply)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor
      
  def getInputVolume(self):
    inputVolume = self.inputVolumeSelector.currentNode()
    if inputVolume is None:
      inputVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    return inputVolume
  
  def onApply(self):
    import SegmentEditorMaskVolumeLib
    inputVolume = self.getInputVolume()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    volumesLogic = slicer.modules.volumes.logic()
    scene = inputVolume.GetScene()
    padExtent = [-self.padEdit.value, self.padEdit.value, -self.padEdit.value, self.padEdit.value, -self.padEdit.value, self.padEdit.value]
    
    # Create a new folder in subject hierarchy where all the generated volumes will be placed into
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene) 
    inputVolumeParentItem = shNode.GetItemParent(shNode.GetItemByDataNode(inputVolume))
    outputShFolder = shNode.CreateFolderItem(inputVolumeParentItem, inputVolume.GetName()+" split")

    # Iterate over segments
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    for segmentIndex in range(segmentationNode.GetSegmentation().GetNumberOfSegments()):
      segmentID = segmentationNode.GetSegmentation().GetNthSegmentID(segmentIndex)
      segmentIDs = vtk.vtkStringArray()
      segmentIDs.InsertNextValue(segmentID)
      
      # Create volume for output
      outputVolumeName = inputVolume.GetName() + '_' + segmentID
      outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)
      
      # Crop segment
      maskExtent = [0] * 6
      SegmentEditorMaskVolumeLib.SegmentEditorEffect.maskVolumeWithSegment(self, segmentationNode, segmentID, "FILL_OUTSIDE", [0], inputVolume, outputVolume, maskExtent)
      
      # Calculate padded extent of segment
      extent = [0] * 6
      for i in range(len(extent)):
        extent[i] = maskExtent[i] + padExtent[i]

      # Calculate the new origin
      ijkToRas = vtk.vtkMatrix4x4()
      outputVolume.GetIJKToRASMatrix(ijkToRas)
      origin_IJK = [extent[0], extent[2], extent[4], 1]
      origin_RAS = ijkToRas.MultiplyPoint(origin_IJK)

      # Pad and crop
      padFilter = vtk.vtkImageConstantPad()
      padFilter.SetInputData(outputVolume.GetImageData())
      padFilter.SetConstant(self.fillValueEdit.value)
      padFilter.SetOutputWholeExtent(extent)
      padFilter.Update()
      paddedImg = padFilter.GetOutput()

      # Normalize output image
      paddedImg.SetOrigin(0,0,0)
      paddedImg.SetSpacing(1.0, 1.0, 1.0)
      paddedImg.SetExtent(0, extent[1]-extent[0], 0, extent[3]-extent[2], 0, extent[5]-extent[4])
      outputVolume.SetAndObserveImageData(paddedImg)
      outputVolume.SetOrigin(origin_RAS[0], origin_RAS[1], origin_RAS[2])

      # Place output image in subject hierarchy folder
      shNode.SetItemParent(shNode.GetItemByDataNode(outputVolume), outputShFolder)

    qt.QApplication.restoreOverrideCursor()
