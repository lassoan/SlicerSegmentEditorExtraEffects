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
    return """<html>Use the currently selected segment to define the cropped image extent. Cropping is applied to the master volume by default. Optionally, padding can be added to the output image in each axis.<p>
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
 
    self.inputVisibilityButton = qt.QToolButton()
    self.inputVisibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))
    self.inputVisibilityButton.setAutoRaise(True)
    self.inputVisibilityButton.setCheckable(True)
    self.inputVisibilityButton.connect('clicked()', self.onInputVisibilityButtonClicked)
    inputLayout = qt.QHBoxLayout()
    inputLayout.addWidget(self.inputVisibilityButton)
    inputLayout.addWidget(self.inputVolumeSelector)
    self.scriptedEffect.addLabeledOptionsWidget("Input Volume: ", inputLayout)
 
    # output volume selector
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode", "vtkMRMLLabelMapVolumeNode"]
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.renameEnabled = True
    self.outputVolumeSelector.noneEnabled = True
    self.outputVolumeSelector.noneDisplay = "(Create new Volume)"
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.outputVolumeSelector.setToolTip("Cropped output volume. It may be the same as the input volume for cumulative cropping.")
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onOutputVolumeChanged)
 
    self.outputVisibilityButton = qt.QToolButton()
    self.outputVisibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))
    self.outputVisibilityButton.setAutoRaise(True)
    self.outputVisibilityButton.setCheckable(True)
    self.outputVisibilityButton.connect('clicked()', self.onOutputVisibilityButtonClicked)
    outputLayout = qt.QHBoxLayout()
    outputLayout.addWidget(self.outputVisibilityButton)
    outputLayout.addWidget(self.outputVolumeSelector)
    self.scriptedEffect.addLabeledOptionsWidget("Output Volume: ", outputLayout)
     
    # X pad value
    self.xPad = qt.QSpinBox()
    self.xPad.setToolTip("Choose the number of voxels used to pad the image in the X-axis")
    self.xPad.minimum = 0
    self.xPad.maximum = 1000
    self.xPad.connect("valueChanged(int)", self.onVoxelXPadValueChanged)
    self.xPadLabel = qt.QLabel("X Pad voxels: ")
     
    self.xPadPercent = qt.QSpinBox()
    self.xPadPercent.setToolTip("Choose size of the padding in the X-axis as a percent of the original image size")
    self.xPadPercent.minimum = 0
    self.xPadPercent.maximum = 100
    self.xPadPercent.connect("valueChanged(double)", self.onVoxelXPadPercentChanged)
    self.xPadPercentLabel = qt.QLabel("X Pad percentage: ")
 
    # Y pad value
    self.yPad = qt.QSpinBox()
    self.yPad.setToolTip("Choose the number of voxels used to pad the image in the Y-axis")
    self.yPad.minimum = 0
    self.yPad.maximum = 1000
    self.yPad.connect("valueChanged(int)", self.onVoxelYPadValueChanged)
    self.yPadLabel = qt.QLabel("Y Pad voxels: ")
     
    self.yPadPercent = qt.QSpinBox()
    self.yPadPercent.setToolTip("Choose size of the padding in the Y-axis as a percent of the original image size")
    self.yPadPercent.minimum = 0
    self.yPadPercent.maximum = 100
    self.yPadPercent.connect("valueChanged(double)", self.onVoxelYPadPercentChanged)
    self.yPadPercentLabel = qt.QLabel("Y Pad percentage: ")
 
    # Z pad value
    self.zPad = qt.QSpinBox()
    self.zPad.setToolTip("Choose the number of voxels used to pad the image in the Z-axis")
    self.zPad.minimum = 0
    self.zPad.maximum = 1000
    self.zPad.connect("valueChanged(int)", self.onVoxelZPadValueChanged)
    self.zPadLabel = qt.QLabel("Z Pad voxels: ")
     
    self.zPadPercent = qt.QSpinBox()
    self.zPadPercent.setToolTip("Choose size of the padding in the Z-axis as a percent of the original image size")
    self.zPadPercent.minimum = 0
    self.zPadPercent.maximum = 100
    self.zPadPercent.connect("valueChanged(double)", self.onVoxelZPadPercentChanged)
    self.zPadPercentLabel = qt.QLabel("Z Pad percentage: ")
 
    # Fill value layouts
    # addWidget(*Widget, row, column, rowspan, colspan)
    padValueLayout = qt.QGridLayout()
    padValueLayout.addWidget(self.xPadLabel,1,1,1,1)
    padValueLayout.addWidget(self.xPad,1,2,1,1)
    padValueLayout.addWidget(self.xPadPercentLabel,1,3,1,1)
    padValueLayout.addWidget(self.xPadPercent,1,4,1,1)
    padValueLayout.addWidget(self.yPadLabel,2,1,1,1)
    padValueLayout.addWidget(self.yPad,2,2,1,1)
    padValueLayout.addWidget(self.yPadPercentLabel,2,3,1,1)
    padValueLayout.addWidget(self.yPadPercent,2,4,1,1)
    padValueLayout.addWidget(self.zPadLabel,3,1,1,1)
    padValueLayout.addWidget(self.zPad,3,2,1,1)
    padValueLayout.addWidget(self.zPadPercentLabel,3,3,1,1)
    padValueLayout.addWidget(self.zPadPercent,3,4,1,1)

    self.scriptedEffect.addOptionsWidget(padValueLayout)
    
    self.fillValue = qt.QSpinBox()
    self.fillValue.setToolTip("Value that the image will be padded with")
    self.fillValue.minimum = 0
    self.fillValue.maximum = 1000
    self.fillValueLabel = qt.QLabel("Fill value: ")
    
    fillValueLayout = qt.QFormLayout()
    fillValueLayout.addRow(self.fillValueLabel, self.fillValue)
    self.scriptedEffect.addOptionsWidget(fillValueLayout)     
    
    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Crop image using the extent of the active segment. No undo operation available once applied.")
    self.scriptedEffect.addOptionsWidget(self.applyButton)
    self.applyButton.connect('clicked()', self.onApply)
 
  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor
 
  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("InputVisibility", "True")
    self.scriptedEffect.setParameterDefault("OutputVisibility", "False")
   
  def onVoxelXPadValueChanged(self):
    #reset percentage boxes to match voxel number
    dimension = self.getInputVolume().GetImageData().GetDimensions() 
    xValue = float(self.xPad.value)/dimension[0]*100
    if(abs(xValue-self.xPadPercent.value) > 1):
      self.xPadPercent.setValue( round(xValue,2) )

  def onVoxelYPadValueChanged(self):
    #reset percentage boxes to match voxel number
    dimension = self.getInputVolume().GetImageData().GetDimensions()       
    yValue = float(self.yPad.value)/dimension[1]*100
    if(abs(yValue-self.yPadPercent.value) > 1):
      self.yPadPercent.setValue( round(yValue,2) )
    
  def onVoxelZPadValueChanged(self):
    #reset percentage boxes to match voxel number
    dimension = self.getInputVolume().GetImageData().GetDimensions()     
    zValue = float(self.zPad.value)/dimension[2]*100
    if(abs(zValue-self.zPadPercent.value) > 1):
      self.zPadPercent.setValue( round(zValue,2) )
    
  def onVoxelXPadPercentChanged(self):
    #reset voxel boxes to match percents
    dimension = self.getInputVolume().GetImageData().GetDimensions() 
    xValue = float(self.xPadPercent.value)/100*dimension[0]
    if(abs(xValue-self.xPad.value) > 1):
      self.xPad.setValue( round(xValue) )

  def onVoxelYPadPercentChanged(self):
    #reset voxel boxes to match percents 
    dimension = self.getInputVolume().GetImageData().GetDimensions() 
    yValue = float(self.yPadPercent.value)/100*dimension[1]
    if(abs(yValue-self.yPad.value) > 1):
      self.yPad.setValue( round(yValue) )

  def onVoxelZPadPercentChanged(self):
    #reset voxel boxes to match percents
    dimension = self.getInputVolume().GetImageData().GetDimensions()  
    zValue = float(self.zPadPercent.value)/100*dimension[2]
    if(abs(zValue-self.zPad.value) > 1):
      self.zPad.setValue( round(zValue) ) 
     
  def updateGUIFromMRML(self):
    inputVisible = self.scriptedEffect.parameter("InputVisibility")
    outputVisible = self.scriptedEffect.parameter("OutputVisibility")
    inputVolume = self.inputVolumeSelector.currentNode()
    if inputVolume is None:
      inputVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    outputVolume = self.outputVolumeSelector.currentNode()
    masterVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    visibleIcon = qt.QIcon(":/Icons/Small/SlicerVisible.png")
    invisibleIcon = qt.QIcon(":/Icons/Small/SlicerInvisible.png")
    if inputVisible == "True" and outputVisible == "True":
      self.inputVisibilityButton.setIcon(visibleIcon)
      self.outputVisibilityButton.setIcon(visibleIcon)
      slicer.util.setSliceViewerLayers(background=inputVolume)
    elif inputVisible == "True":
      self.inputVisibilityButton.setIcon(visibleIcon)
      self.outputVisibilityButton.setIcon(invisibleIcon)
      slicer.util.setSliceViewerLayers(background=inputVolume)
    elif outputVisible == "True":
      self.outputVisibilityButton.setIcon(visibleIcon)
      self.inputVisibilityButton.setIcon(invisibleIcon)
      slicer.util.setSliceViewerLayers(background=outputVolume)
    else:
      self.outputVisibilityButton.setIcon(invisibleIcon)
      self.inputVisibilityButton.setIcon(invisibleIcon)
      slicer.util.setSliceViewerLayers(background=masterVolume)
      self.inputVisibilityButton.setEnabled(False)
 
    self.inputVisibilityButton.setEnabled(not(inputVolume is masterVolume and inputVisible == "True"))
    self.outputVisibilityButton.setEnabled(not((outputVolume is masterVolume and outputVisible == "True") or outputVolume is None))
 
    self.inputVisibilityButton.setChecked(self.inputVisibilityButton.isEnabled() and inputVisible == "True")
    self.outputVisibilityButton.setChecked(self.outputVisibilityButton.isEnabled() and outputVisible == "True")
 
  def activate(self):
    self.scriptedEffect.setParameter("InputVisibility", "True")
 
  def deactivate(self):
    if self.outputVolumeSelector.currentNode() is not self.scriptedEffect.parameterSetNode().GetMasterVolumeNode():
      self.scriptedEffect.setParameter("OutputVisibility", "False")
    slicer.util.setSliceViewerLayers(background=self.scriptedEffect.parameterSetNode().GetMasterVolumeNode())
 
  def onOperationSelectionChanged(self, operationName, toggle):
    if not toggle:
      return
    if self.outputVolumeSelector.noneDisplay != "(Create new Volume)":
      self.outputVolumeSelector.noneDisplay = "(Create new Volume)"
      self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode", "vtkMRMLLabelMapVolumeNode"]
      self.outputVolumeSelector.setCurrentNode(None)
 
  def getInputVolume(self):
    inputVolume = self.inputVolumeSelector.currentNode()
    if inputVolume is None:
      inputVolume = self.scriptedEffect.parameterSetNode().GetMasterVolumeNode()
    return inputVolume
 
  def onInputVisibilityButtonClicked(self):
    if self.inputVisibilityButton.isEnabled():
      if self.inputVisibilityButton.isChecked():
        self.scriptedEffect.setParameter("InputVisibility", "True")
        if self.outputVolumeSelector.currentNode() is self.getInputVolume():
          self.scriptedEffect.setParameter("OutputVisibility", "True")
        elif self.scriptedEffect.parameter("OutputVisibility") == "True":
          self.scriptedEffect.setParameter("OutputVisibility", "False")
      else:
        self.scriptedEffect.setParameter("InputVisibility", "False")
        if self.outputVolumeSelector.currentNode() is self.scriptedEffect.parameterSetNode().GetMasterVolumeNode():
          self.scriptedEffect.setParameter("OutputVisibility", "True")
        elif self.outputVolumeSelector.currentNode() is self.getInputVolume():
          self.scriptedEffect.setParameter("OutputVisibility", "False")
    self.updateGUIFromMRML()
 
  def onOutputVisibilityButtonClicked(self):
    if self.outputVisibilityButton.isEnabled() and self.outputVolumeSelector.currentNode():
      if self.outputVisibilityButton.isChecked():
        self.scriptedEffect.setParameter("OutputVisibility", "True")
        if self.getInputVolume() is self.outputVolumeSelector.currentNode():
          self.scriptedEffect.setParameter("InputVisibility", "True")
        elif self.scriptedEffect.parameter("InputVisibility") == "True":
          self.scriptedEffect.setParameter("InputVisibility", "False")
      else:
        self.scriptedEffect.setParameter("OutputVisibility", "False")
        if self.getInputVolume() is self.scriptedEffect.parameterSetNode().GetMasterVolumeNode():
          self.scriptedEffect.setParameter("InputVisibility", "True")
        elif self.getInputVolume() is self.outputVolumeSelector.currentNode():
          self.scriptedEffect.setParameter("InputVisibility", "False")
    self.updateGUIFromMRML()
 
  def onInputVolumeChanged(self):
    if self.getInputVolume() is self.outputVolumeSelector.currentNode():
      if self.scriptedEffect.parameter("OutputVisibility") == "True":
        self.scriptedEffect.setParameter("InputVisibility", "True")
      elif self.getInputVolume() is self.scriptedEffect.parameterSetNode().GetMasterVolumeNode():
        self.scriptedEffect.setParameter("OutputVisibility", "True")
        self.scriptedEffect.setParameter("InputVisibility", "True")
      else:
        self.scriptedEffect.setParameter("InputVisibility", "False")
    elif self.getInputVolume() is self.scriptedEffect.parameterSetNode().GetMasterVolumeNode() and self.scriptedEffect.parameter("OutputVisibility") == "False":
      self.scriptedEffect.setParameter("InputVisibility", "True")
    else:
      self.scriptedEffect.setParameter("InputVisibility", "False")
    self.updateGUIFromMRML()
 
  def onOutputVolumeChanged(self):
    if self.outputVolumeSelector.currentNode() is self.getInputVolume():
      if self.scriptedEffect.parameter("InputVisibility") == "True":
        self.scriptedEffect.setParameter("OutputVisibility", "True")
      elif self.outputVolumeSelector.currentNode() is self.scriptedEffect.parameterSetNode().GetMasterVolumeNode():
        self.scriptedEffect.setParameter("OutputVisibility", "True")
        self.scriptedEffect.setParameter("InputVisibility", "True")
      else:
        self.scriptedEffect.setParameter("OutputVisibility", "False")
    elif self.outputVolumeSelector.currentNode() is self.scriptedEffect.parameterSetNode().GetMasterVolumeNode() and self.scriptedEffect.parameter("InputVisibility") == "False":
      self.scriptedEffect.setParameter("OutputVisibility", "True")
    else:
      self.scriptedEffect.setParameter("OutputVisibility", "False")
    self.updateGUIFromMRML()
 
  
  def onApply(self):
    inputVolume = self.getInputVolume()
    outputVolume = self.outputVolumeSelector.currentNode()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
     
    if not outputVolume:
      # Create new node for output
      volumesLogic = slicer.modules.volumes.logic()
      scene = inputVolume.GetScene()
      outputVolumeName = inputVolume.GetName()+ segmentID
      outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)
      self.outputVolumeSelector.setCurrentNode(outputVolume)

    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    padExtent = [self.xPad.value, self.zPad.value, self.yPad.value]
    self.cropVolumeWithSegment(segmentationNode, segmentID, inputVolume, outputVolume, padExtent, self.fillValue.value)
    qt.QApplication.restoreOverrideCursor()
 
 
  def cropVolumeWithSegment(self, segmentationNode, segmentID, inputVolumeNode, outputVolumeNode, padRegion, padValue):
    """
    Fill voxels of the input volume inside/outside the Cropping model with the provided fill value
    """
 
    segmentIDs = vtk.vtkStringArray()
    segmentIDs.InsertNextValue(segmentID)
    intensityRange = inputVolumeNode.GetImageData().GetScalarRange()
    maskedVolume = slicer.modules.volumes.logic().CreateAndAddLabelVolume(inputVolumeNode, "TemporaryVolumeCrop")
    if not maskedVolume:
      logging.error("cropVolumeWithSegment failed: invalid maskedVolume")
      return False
 
    if not slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentationNode, segmentIDs, maskedVolume, inputVolumeNode):
      logging.error("cropVolumeWithSegment failed: ExportSegmentsToLabelmapNode error")
      slicer.mrmlScene.RemoveNode(maskedVolume.GetDisplayNode().GetColorNode())
      slicer.mrmlScene.RemoveNode(maskedVolume.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(maskedVolume)
      return False
 
    # Crop to region greater than threshold
    maskToStencil = vtk.vtkImageToImageStencil()
    maskToStencil.ThresholdByLower(0)
    maskToStencil.SetInputData(maskedVolume.GetImageData())
    stencil = vtk.vtkImageStencil()
    stencil.SetInputData(inputVolumeNode.GetImageData())
    stencil.SetStencilConnection(maskToStencil.GetOutputPort())
    stencil.SetReverseStencil(1)
    stencil.SetBackgroundValue(intensityRange[0]-1)
    stencil.Update()
     
    outputVolumeNode.SetAndObserveImageData(stencil.GetOutput())
    # Set the same geometry and parent transform as the input volume
    ijkToRas = vtk.vtkMatrix4x4()
    inputVolumeNode.GetIJKToRASMatrix(ijkToRas)
    outputVolumeNode.SetIJKToRASMatrix(ijkToRas)
    inputVolumeNode.SetAndObserveTransformNodeID(inputVolumeNode.GetTransformNodeID())
     
    # Get masked output as a vtk oriented image and crop
    cropThreshold = 0
    img = slicer.modules.segmentations.logic().CreateOrientedImageDataFromVolumeNode(outputVolumeNode) 
    img.UnRegister(None) 
    extent=[0,0,0,0,0,0]
    vtkSegmentationCore.vtkOrientedImageDataResample.CalculateEffectiveExtent(img, extent, cropThreshold) 
    croppedImg = vtkSegmentationCore.vtkOrientedImageData() 
    vtkSegmentationCore.vtkOrientedImageDataResample.CopyImage(img, croppedImg, extent) 
    slicer.modules.segmentations.logic().CopyOrientedImageDataToVolumeNode(croppedImg, outputVolumeNode)
    
    # Use ITK to apply pad to image
    itkImage = sitkUtils.PullVolumeFromSlicer(outputVolumeNode) 
    padFilter = sitk.ConstantPadImageFilter()# apply pad
    padFilter.SetPadUpperBound(padRegion)
    padFilter.SetPadLowerBound(padRegion)
    padFilter.SetConstant(padValue)
    paddedImage = padFilter.Execute(itkImage)
    sitkUtils.PushVolumeToSlicer(paddedImage,outputVolumeNode)
    
    slicer.mrmlScene.RemoveNode(maskedVolume.GetDisplayNode().GetColorNode())
    slicer.mrmlScene.RemoveNode(maskedVolume.GetDisplayNode())
    slicer.mrmlScene.RemoveNode(maskedVolume)
    return True
