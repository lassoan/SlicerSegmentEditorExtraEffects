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
    return """Create a volume node for each visible segment, or only the selected segment, cropped to the segment extent.\n
Extent is expanded by the specified number of padding voxels along each axis. Voxels outside the segment are set to the requested fill value.
Generated volumes are not affected by segmentation undo/redo operations.
</html>"""

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("FillValue", "0")
    self.scriptedEffect.setParameterDefault("PaddingVoxels", "5")
    self.scriptedEffect.setParameterDefault("ApplyToAllVisibleSegments", "1")

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

    wasBlocked = self.applyToAllVisibleSegmentsCheckBox.blockSignals(True)
    checked = (self.scriptedEffect.integerParameter("ApplyToAllVisibleSegments") != 0)
    self.applyToAllVisibleSegmentsCheckBox.setChecked(checked)
    self.applyToAllVisibleSegmentsCheckBox.blockSignals(wasBlocked)

  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("FillValue", self.fillValueEdit.value)
    self.scriptedEffect.setParameter("PaddingVoxels", self.padEdit.value)
    self.scriptedEffect.setParameter("ApplyToAllVisibleSegments", "1" if  (self.applyToAllVisibleSegmentsCheckBox.isChecked()) else "0")

  def onAllSegmentsCheckboxStateChanged(self, newState):
    self.scriptedEffect.setParameter("ApplyToAllVisibleSegments", "1" if  (self.applyToAllVisibleSegmentsCheckBox.isChecked()) else "0")

  def setupOptionsFrame(self):

    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = True
    self.inputVolumeSelector.addEnabled = True
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.noneEnabled = True
    self.inputVolumeSelector.noneDisplay = "(Source volume)"
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.inputVolumeSelector.setToolTip("Volume to split. Default is current source volume node.")
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

    # Segment scope checkbox layout
    self.applyToAllVisibleSegmentsCheckBox = qt.QCheckBox()
    self.applyToAllVisibleSegmentsCheckBox.setChecked(True)
    self.applyToAllVisibleSegmentsCheckBox.setToolTip("Apply to all visible segments, or only the selected segment.")
    self.scriptedEffect.addLabeledOptionsWidget("Apply to visible segments: ", self.applyToAllVisibleSegmentsCheckBox)
    # Connection
    self.applyToAllVisibleSegmentsCheckBox.connect('stateChanged(int)', self.onAllSegmentsCheckboxStateChanged)

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
      if slicer.app.majorVersion == 5 and slicer.app.minorVersion >= 1:
        inputVolume = self.scriptedEffect.parameterSetNode().GetSourceVolumeNode()
      else:
        inputVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    return inputVolume

  def onApply(self):
    import SegmentEditorEffects
    if not hasattr(SegmentEditorEffects,'SegmentEditorMaskVolumeEffect'):
      # Slicer 4.11 and earlier - Mask volume is in an extension
      import SegmentEditorMaskVolumeLib
      maskVolumeWithSegment = SegmentEditorMaskVolumeLib.SegmentEditorEffect.maskVolumeWithSegment
    else:
      maskVolumeWithSegment = SegmentEditorEffects.SegmentEditorMaskVolumeEffect.maskVolumeWithSegment

    inputVolume = self.getInputVolume()
    currentSegmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    volumesLogic = slicer.modules.volumes.logic()
    scene = inputVolume.GetScene()
    padExtent = [-self.padEdit.value, self.padEdit.value, -self.padEdit.value, self.padEdit.value, -self.padEdit.value, self.padEdit.value]
    fillValue = self.fillValueEdit.value

    # Create a new folder in subject hierarchy where all the generated volumes will be placed into
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    inputVolumeParentItem = shNode.GetItemParent(shNode.GetItemByDataNode(inputVolume))
    outputShFolder = shNode.CreateFolderItem(inputVolumeParentItem, inputVolume.GetName()+" split")

    # Filter out visible segments, or only the selected segment, irrespective of its visibility.
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    visibleSegmentIDs = vtk.vtkStringArray()
    segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIDs)
    if (self.scriptedEffect.integerParameter("ApplyToAllVisibleSegments") != 0):
        inputSegments = []
        for segmentIndex in range(visibleSegmentIDs.GetNumberOfValues()):
            inputSegments.append(visibleSegmentIDs.GetValue(segmentIndex))
    else:
        inputSegments = [currentSegmentID]
    # Iterate over targeted segments
    for segmentID in inputSegments:
      # Create volume for output
      outputVolumeName = inputVolume.GetName() + ' ' + segmentationNode.GetSegmentation().GetSegment(segmentID).GetName()
      outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)

      # Crop segment
      maskExtent = [0] * 6
      maskVolumeWithSegment(segmentationNode, segmentID, "FILL_OUTSIDE", [fillValue], inputVolume, outputVolume, maskExtent)

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
      padFilter.SetConstant(fillValue)
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
