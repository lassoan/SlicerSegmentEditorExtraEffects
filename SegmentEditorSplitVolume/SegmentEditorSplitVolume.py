import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

class SegmentEditorSplitVolume(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    import string
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SegmentEditorSplitVolume"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = ["Segmentations"]
    self.parent.contributors = [ "Sara Rolfe (UW, Seattle)", "Murat Maga (UW)", "Andras Lasso (PerkLab, Queen's)"]
    self.parent.hidden = True
    self.parent.helpText = "This hidden module registers the segment editor effect"
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
    Supported by an NSF ABI Development grant, "An Integrated Platform for Retrieval, Visualization and Analysis of
    3D Morphology From Digital Biological Collections" (Award Numbers: 1759883 (Murat Maga), 1759637 (Adam Summers), 1759839 (Douglas Boyer)).
    https://nsf.gov/awardsearch/showAward?AWD_ID=1759883&HistoricalAwards=false
    """
    slicer.app.connect("startupCompleted()", self.registerEditorEffect)

  def registerEditorEffect(self):
    import qSlicerSegmentationsEditorEffectsPythonQt as qSlicerSegmentationsEditorEffects
    instance = qSlicerSegmentationsEditorEffects.qSlicerSegmentEditorScriptedEffect(None)
    effectFilename = os.path.join(os.path.dirname(__file__), self.__class__.__name__+'Lib/SegmentEditorEffect.py')
    instance.setPythonSource(effectFilename.replace('\\','/'))
    instance.self().register()

class SegmentEditorSplitVolumeTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SplitVolume1()

  def test_SplitVolume1(self):
    """
    Basic automated test of the segmentation method:
    - Create segmentation by placing sphere-shaped seeds
    - Run segmentation
    - Verify results using segment statistics
    The test can be executed from SelfTests module (test name: SegmentEditorSplitVolume)
    """

    self.delayDisplay("Starting test_SplitVolume1")

    import vtkSegmentationCorePython as vtkSegmentationCore
    import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic
    import SampleData
    from SegmentStatistics import SegmentStatisticsLogic

    ##################################
    self.delayDisplay("Load master volume")

    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    masterVolumeNode = sampleDataLogic.downloadMRBrainTumor1()

    ##################################
    self.delayDisplay("Create segmentation containing a few spheres")

    segmentationNode = slicer.vtkMRMLSegmentationNode()
    slicer.mrmlScene.AddNode(segmentationNode)
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)

    # Segments are defined by a list of: name and a list of sphere [radius, posX, posY, posZ]
    segmentGeometries = [
      ['Tumor', [[10, -6,30,28]]],
      ['Background', [[10, 0,65,22], [15, 1, -14, 30], [12, 0, 28, -7], [5, 0,30,54], [12, 31, 33, 27], [17, -42, 30, 27], [6, -2,-17,71]]],
      ['Air', [[10, 76,73,0], [15, -70,74,0]]] ]
    for segmentGeometry in segmentGeometries:
      segmentName = segmentGeometry[0]
      appender = vtk.vtkAppendPolyData()
      for sphere in segmentGeometry[1]:
        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetRadius(sphere[0])
        sphereSource.SetCenter(sphere[1], sphere[2], sphere[3])
        appender.AddInputConnection(sphereSource.GetOutputPort())
      segment = vtkSegmentationCore.vtkSegment()
      segment.SetName(segmentationNode.GetSegmentation().GenerateUniqueSegmentID(segmentName))
      appender.Update()
      segment.AddRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(), appender.GetOutput())
      segmentationNode.GetSegmentation().AddSegment(segment)

    ##################################
    self.delayDisplay("Create segment editor")

    segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    segmentEditorWidget.show()
    segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
    segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
    slicer.mrmlScene.AddNode(segmentEditorNode)
    segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    segmentEditorWidget.setSegmentationNode(segmentationNode)
    if slicer.app.majorVersion == 5 and slicer.app.minorVersion >= 1:
      segmentEditorWidget.setSourceVolumeNode(masterVolumeNode)
    else:
      segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)

    ##################################
    self.delayDisplay("Run segmentation")
    segmentEditorWidget.setActiveEffectByName("SplitVolume")
    effect = segmentEditorWidget.activeEffect()
    effect.self().onApply()

    ##################################
    self.delayDisplay("Make segmentation results nicely visible in 3D")
    segmentationDisplayNode = segmentationNode.GetDisplayNode()
    segmentationDisplayNode.SetSegmentVisibility("Air", False)
    segmentationDisplayNode.SetSegmentOpacity3D("Background",0.5)

    ##################################
    self.delayDisplay("Check extent of cropped volumes")
    expectedBounds = [
      [100.31225000000003, 119.99975000000003, 101.24974999999999, 119.99974999999999, -78.4, -58.8],
      [19.68725000000002, 119.99975000000003, 16.874749999999977, 119.99974999999999, -78.4, 16.80000000000001],
      [-49.687749999999994, 119.99975000000003, 90.93724999999999, 119.99974999999999, -78.4, -47.6] ]

    for segmentIndex in range(segmentationNode.GetSegmentation().GetNumberOfSegments()):
      segmentID = segmentationNode.GetSegmentation().GetNthSegmentID(segmentIndex)
      outputVolumeName = masterVolumeNode.GetName() + '_' + segmentID
      outputVolume = slicer.util.getNode(outputVolumeName)
      bounds=[0,0,0,0,0,0]
      outputVolume.GetBounds(bounds)
      self.assertEqual( bounds, expectedBounds)


    ##################################
    self.delayDisplay("Compute statistics")

    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)

    # Export results to table (just to see all results)
    resultsTableNode = slicer.vtkMRMLTableNode()
    slicer.mrmlScene.AddNode(resultsTableNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)

    self.delayDisplay("Check a few numerical results")
    self.assertEqual( round(segStatLogic.statistics["Tumor","LM volume cc"]), 16)
    self.assertEqual( round(segStatLogic.statistics["Background","LM volume cc"]), 3010)

    self.delayDisplay('test_SplitVolume1 passed')
