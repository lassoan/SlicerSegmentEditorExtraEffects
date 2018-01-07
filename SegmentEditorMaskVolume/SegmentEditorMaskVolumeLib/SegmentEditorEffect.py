import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses a currently existing segment to mask the master volume with a chosen voxel fill value."""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Mask volume'
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
    return """<html>Use the currently selected segment as a mask.<br> The mask is applied to the master volume by default.<p>
Fill inside and outside operation creates a binary labelmap volume as output, with the inside and outside fill values
modifiable.
</html>"""

  def setupOptionsFrame(self):
    self.operationRadioButtons = []

    # Fill operation buttons
    self.fillInsideButton = qt.QRadioButton("Fill inside")
    self.operationRadioButtons.append(self.fillInsideButton)
    self.buttonToOperationNameMap[self.fillInsideButton] = 'FILL_INSIDE'

    self.fillOutsideButton = qt.QRadioButton("Fill outside")
    self.operationRadioButtons.append(self.fillOutsideButton)
    self.buttonToOperationNameMap[self.fillOutsideButton] = 'FILL_OUTSIDE'

    self.binaryMaskFillButton = qt.QRadioButton("Fill inside and outside")
    self.binaryMaskFillButton.setToolTip("Create a labelmap volume with specified inside and outside fill values.")
    self.operationRadioButtons.append(self.binaryMaskFillButton)
    self.buttonToOperationNameMap[self.binaryMaskFillButton] = 'FILL_INSIDE_AND_OUTSIDE'

    # Operation buttons layout
    operationLayout = qt.QGridLayout()
    operationLayout.addWidget(self.fillInsideButton, 0, 0)
    operationLayout.addWidget(self.fillOutsideButton, 1, 0)
    operationLayout.addWidget(self.binaryMaskFillButton, 0, 1)
    self.scriptedEffect.addLabeledOptionsWidget("Operation:", operationLayout)

    # fill value
    self.fillValueEdit = qt.QSpinBox()
    self.fillValueEdit.setToolTip("Choose the voxel intensity that will be used to fill the masked region.")
    self.fillValueEdit.minimum = -32768
    self.fillValueEdit.maximum = 65535
    self.fillValueEdit.connect("valueChanged(int)", self.fillValueChanged)
    self.fillValueLabel = qt.QLabel("Fill value: ")

    # Binary mask fill outside value
    self.binaryMaskFillOutsideEdit = qt.QSpinBox()
    self.binaryMaskFillOutsideEdit.setToolTip("Choose the voxel intensity that will be used to fill outside the mask.")
    self.binaryMaskFillOutsideEdit.minimum = -32768
    self.binaryMaskFillOutsideEdit.maximum = 65535
    self.binaryMaskFillOutsideEdit.connect("valueChanged(int)", self.fillValueChanged)
    self.fillOutsideLabel = qt.QLabel("Outside fill value: ")

    # Binary mask fill outside value
    self.binaryMaskFillInsideEdit = qt.QSpinBox()
    self.binaryMaskFillInsideEdit.setToolTip("Choose the voxel intensity that will be used to fill inside the mask.")
    self.binaryMaskFillInsideEdit.minimum = -32768
    self.binaryMaskFillInsideEdit.maximum = 65535
    self.binaryMaskFillInsideEdit.connect("valueChanged(int)", self.fillValueChanged)
    self.fillInsideLabel = qt.QLabel(" Inside fill value: ")

    # Fill value layouts
    fillValueLayout = qt.QFormLayout()
    fillValueLayout.addRow(self.fillValueLabel, self.fillValueEdit)

    fillOutsideLayout = qt.QFormLayout()
    fillOutsideLayout.addRow(self.fillOutsideLabel, self.binaryMaskFillOutsideEdit)

    fillInsideLayout = qt.QFormLayout()
    fillInsideLayout.addRow(self.fillInsideLabel, self.binaryMaskFillInsideEdit)

    binaryMaskFillLayout = qt.QHBoxLayout()
    binaryMaskFillLayout.addLayout(fillOutsideLayout)
    binaryMaskFillLayout.addLayout(fillInsideLayout)
    fillValuesSpinBoxLayout = qt.QFormLayout()
    fillValuesSpinBoxLayout.addRow(binaryMaskFillLayout)
    fillValuesSpinBoxLayout.addRow(fillValueLayout)
    self.scriptedEffect.addOptionsWidget(fillValuesSpinBoxLayout)

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
    self.inputVolumeSelector.setToolTip("Volume to mask. Default is current master volume node.")
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
    self.outputVolumeSelector.setToolTip("Masked output volume. It may be the same as the input volume for cumulative masking.")
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

    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Apply segment as volume mask. No undo operation available once applied.")
    self.scriptedEffect.addOptionsWidget(self.applyButton)
    self.applyButton.connect('clicked()', self.onApply)

    for button in self.operationRadioButtons:
      button.connect('toggled(bool)',
      lambda toggle, widget=self.buttonToOperationNameMap[button]: self.onOperationSelectionChanged(widget, toggle))

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("FillValue", "0")
    self.scriptedEffect.setParameterDefault("BinaryMaskFillValueInside", "1")
    self.scriptedEffect.setParameterDefault("BinaryMaskFillValueOutside", "0")
    self.scriptedEffect.setParameterDefault("Operation", "FILL_OUTSIDE")
    self.scriptedEffect.setParameterDefault("InputVisibility", "True")
    self.scriptedEffect.setParameterDefault("OutputVisibility", "False")

  def updateGUIFromMRML(self):
    self.fillValueEdit.setValue(float(self.scriptedEffect.parameter("FillValue")))
    self.binaryMaskFillOutsideEdit.setValue(float(self.scriptedEffect.parameter("BinaryMaskFillValueOutside")))
    self.binaryMaskFillInsideEdit.setValue(float(self.scriptedEffect.parameter("BinaryMaskFillValueInside")))
    operationButton = [key for key, value in self.buttonToOperationNameMap.iteritems() if value == self.scriptedEffect.parameter("Operation")][0]
    operationButton.setChecked(True)

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

  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("FillValue", self.fillValueEdit.value)
    self.scriptedEffect.setParameter("BinaryMaskFillValueInside", self.binaryMaskFillInsideEdit.value)
    self.scriptedEffect.setParameter("BinaryMaskFillValueOutside", self.binaryMaskFillOutsideEdit.value)

  def activate(self):
    self.scriptedEffect.setParameter("InputVisibility", "True")

  def deactivate(self):
    if self.outputVolumeSelector.currentNode() is not self.scriptedEffect.parameterSetNode().GetMasterVolumeNode():
      self.scriptedEffect.setParameter("OutputVisibility", "False")
    slicer.util.setSliceViewerLayers(background=self.scriptedEffect.parameterSetNode().GetMasterVolumeNode())

  def onOperationSelectionChanged(self, operationName, toggle):
    if not toggle:
      return
    self.fillValueEdit.setVisible(operationName in ["FILL_INSIDE", "FILL_OUTSIDE"])
    self.fillValueLabel.setVisible(operationName in ["FILL_INSIDE", "FILL_OUTSIDE"])
    self.binaryMaskFillInsideEdit.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
    self.fillInsideLabel.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
    self.binaryMaskFillOutsideEdit.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
    self.fillOutsideLabel.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
    self.scriptedEffect.setParameter("Operation", operationName)
    if operationName in ["FILL_INSIDE", "FILL_OUTSIDE"]:
      if self.outputVolumeSelector.noneDisplay != "(Create new Volume)":
        self.outputVolumeSelector.noneDisplay = "(Create new Volume)"
        self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode", "vtkMRMLLabelMapVolumeNode"]
        self.outputVolumeSelector.setCurrentNode(None)
    else:
      if self.outputVolumeSelector.noneDisplay != "(Create new Labelmap Volume)":
        self.outputVolumeSelector.noneDisplay = "(Create new Labelmap Volume)"
        self.outputVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode", "vtkMRMLScalarVolumeNode"]
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

  def fillValueChanged(self):
    self.updateMRMLFromGUI()

  def onApply(self):
    inputVolume = self.getInputVolume()
    outputVolume = self.outputVolumeSelector.currentNode()
    operationMode = self.scriptedEffect.parameter("Operation")
    if not outputVolume:
      # Create new node for output
      volumesLogic = slicer.modules.volumes.logic()
      scene = inputVolume.GetScene()
      if operationMode == "FILL_INSIDE_AND_OUTSIDE":
        outputVolumeName = inputVolume.GetName()+" label"
        outputVolume = volumesLogic.CreateAndAddLabelVolume(inputVolume, outputVolumeName)
      else:
        outputVolumeName = inputVolume.GetName()+" masked"
        outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)
      self.outputVolumeSelector.setCurrentNode(outputVolume)

    if operationMode in ["FILL_INSIDE", "FILL_OUTSIDE"]:
      fillValues = [self.fillValueEdit.value]
    else:
      fillValues = [self.binaryMaskFillInsideEdit.value, self.binaryMaskFillOutsideEdit.value]

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()

    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    self.maskVolumeWithSegment(segmentationNode, segmentID, operationMode, fillValues, inputVolume, outputVolume)
    qt.QApplication.restoreOverrideCursor()


  def maskVolumeWithSegment(self, segmentationNode, segmentID, operationMode, fillValues, inputVolumeNode, outputVolumeNode):
    """
    Fill voxels of the input volume inside/outside the masking model with the provided fill value
    """

    segmentIDs = vtk.vtkStringArray()
    segmentIDs.InsertNextValue(segmentID)
    maskVolumeNode = slicer.modules.volumes.logic().CreateAndAddLabelVolume(inputVolumeNode, "TemporaryVolumeMask")
    if not maskVolumeNode:
      logging.error("maskVolumeWithSegment failed: invalid maskVolumeNode")
      return False

    if not slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentationNode, segmentIDs, maskVolumeNode, inputVolumeNode):
      logging.error("maskVolumeWithSegment failed: ExportSegmentsToLabelmapNode error")
      slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode().GetColorNode())
      slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(maskVolumeNode)
      return False

    maskToStencil = vtk.vtkImageToImageStencil()
    maskToStencil.ThresholdByLower(0)
    maskToStencil.SetInputData(maskVolumeNode.GetImageData())

    stencil = vtk.vtkImageStencil()

    if operationMode == "FILL_INSIDE_AND_OUTSIDE":
      # Set input to constant value
      thresh = vtk.vtkImageThreshold()
      thresh.SetInputData(inputVolumeNode.GetImageData())
      thresh.ThresholdByLower(0)
      thresh.SetInValue(fillValues[1])
      thresh.SetOutValue(fillValues[1])
      thresh.SetOutputScalarType(inputVolumeNode.GetImageData().GetScalarType())
      thresh.Update()
      stencil.SetInputData(thresh.GetOutput())
    else:
      stencil.SetInputData(inputVolumeNode.GetImageData())

    stencil.SetStencilConnection(maskToStencil.GetOutputPort())
    stencil.SetReverseStencil(operationMode == "FILL_OUTSIDE")
    stencil.SetBackgroundValue(fillValues[0])
    stencil.Update()

    outputVolumeNode.SetAndObserveImageData(stencil.GetOutput())

    # Set the same geometry and parent transform as the input volume
    ijkToRas = vtk.vtkMatrix4x4()
    inputVolumeNode.GetIJKToRASMatrix(ijkToRas)
    outputVolumeNode.SetIJKToRASMatrix(ijkToRas)
    inputVolumeNode.SetAndObserveTransformNodeID(inputVolumeNode.GetTransformNodeID())

    slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode().GetColorNode())
    slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode())
    slicer.mrmlScene.RemoveNode(maskVolumeNode)
    return True
