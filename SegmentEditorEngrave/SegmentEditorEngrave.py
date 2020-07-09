import os
import qt, slicer
from slicer.ScriptedLoadableModule import *

class SegmentEditorEngrave(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SegmentEditorEngrave"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = ["Segmentations"]
    self.parent.contributors = ["Andras Lasso (PerkLab, Queen's)"]
    self.parent.hidden = True
    self.parent.helpText = "This hidden module registers the segment editor effect"
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = "Supported by NA-MIC, NAC, BIRN, NCIGT, and the Slicer Community. " \
                                      "See http://www.slicer.org for details."
    slicer.app.connect("startupCompleted()", self.registerEditorEffect)

  def registerEditorEffect(self):
    import qSlicerSegmentationsEditorEffectsPythonQt as qSlicerSegmentationsEditorEffects
    instance = qSlicerSegmentationsEditorEffects.qSlicerSegmentEditorScriptedEffect(None)
    effectFilename = os.path.join(os.path.dirname(__file__), self.__class__.__name__+'Lib/SegmentEditorEffect.py')
    instance.setPythonSource(effectFilename.replace('\\','/'))
    instance.self().register()

class SegmentEditorEngraveTest(ScriptedLoadableModuleTest):
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
    self.test_Engrave1()

  def test_Engrave1(self):
    """
    Basic automated test of the segmentation method:
    - Create segmentation by placing fiducials around tumor
    - Apply
    - Verify results using segment statistics
    The test can be executed from SelfTests module (test name: SegmentEditorEngrave)
    """

    self.delayDisplay("Starting test_Engrave1")


    ##################################
    self.delayDisplay("Load master volume")

    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    masterVolumeNode = sampleDataLogic.downloadMRBrainTumor1()

    ##################################
    self.delayDisplay("Create tumor segmentation")

    segmentationNode = slicer.vtkMRMLSegmentationNode()
    slicer.mrmlScene.AddNode(segmentationNode)
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)

    segmentName = "Tumor"
    import vtkSegmentationCorePython as vtkSegmentationCore

    segment = vtkSegmentationCore.vtkSegment()
    segment.SetName(segmentationNode.GetSegmentation().GenerateUniqueSegmentID(segmentName))
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
    segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)

    ##################################
    self.delayDisplay("Run segmentation")

    segmentEditorWidget.setActiveEffectByName("ENgrave")
    effect = segmentEditorWidget.activeEffect()

    # effect.self().fiducialPlacementToggle.placeButton().click()

    # points =[[2.589283578714074, 44.60536690073953, 27.299999999999997], [8.515228351086698, 35.22262101114956, 27.299999999999997],
    #          [13.700430026912741, 25.099132025013006, 27.299999999999997], [5.799170330415919, 19.17318725264039, 27.299999999999997],
    #          [2.589283578714074, 9.296612632019361, 27.299999999999997], [-10.250263428093263, 12.25958501820567, 27.299999999999997],
    #          [-16.17620820046588, 18.185529790578286, 27.299999999999997], [-20.373752414229813, 27.568275680168263, 27.299999999999997],
    #          [-15.929293834950343, 38.679422128366916, 27.299999999999997], [-11.484835255670887, 44.11153816970849, 27.299999999999997],
    #          [6.539913426962492, 33.49422045254088, 31.499999999999993], [1.354711751136449, 42.383137611099805, 31.499999999999993],
    #          [-8.768777235000101, 44.35845253522401, 31.499999999999993], [-14.200893276341674, 36.70410720424271, 31.499999999999993],
    #          [-18.398437490105607, 27.07444694913721, 31.499999999999993], [-12.719407083248512, 16.704043597485132, 31.499999999999993],
    #          [-7.534205407422476, 11.765756287174618, 31.499999999999993], [0.12013992355882408, 12.25958501820567, 31.499999999999993],
    #          [5.799170330415919, 16.21021486645408, 31.499999999999993], [8.268313985571176, 21.642330907795646, 31.499999999999993],
    #          [13.947344392428263, 26.827532583621682, 31.499999999999993], [-3.0897468281430065, 32.50656299047878, 45.49999999999998],
    #          [2.589283578714074, 27.32136131465274, 45.49999999999998], [-5.3119761177827485, 21.642330907795646, 45.49999999999998],
    #          [-8.02803413845352, 27.32136131465274, 45.49999999999998], [-14.694722007372718, 30.778162431870093, 38.499999999999986],
    #          [-8.02803413845352, 12.01267065269014, 38.499999999999986], [-3.583575559174065, 39.66707959042902, 11.900000000000007],
    #          [3.576941040776184, 31.765819893932196, 11.900000000000007], [0.12013992355882408, 20.901587811249065, 11.900000000000007],
    #          [-9.26260596603116, 28.555933142230366, 11.900000000000007], [6.046084695931441, 38.432507762851394, 17.500000000000007],
    #          [-17.163865662527982, 33.7411348180564, 17.500000000000007], [-14.200893276341674, 21.889245273311168, 17.500000000000007]]

    # for p in points:
    #   effect.self().segmentMarkupNode.AddFiducialFromArray(p)

    # effect.self().onApply()

    # ##################################
    # self.delayDisplay("Make segmentation results nicely visible in 3D")
    # segmentationDisplayNode = segmentationNode.GetDisplayNode()
    # segmentationDisplayNode.SetSegmentVisibility(segmentName, True)
    # slicer.util.findChild(segmentEditorWidget, "Show3DButton").checked = True
    # segmentationDisplayNode.SetSegmentOpacity3D("Background",0.5)

    # ##################################
    # self.delayDisplay("Compute statistics")

    # from SegmentStatistics import SegmentStatisticsLogic

    # segStatLogic = SegmentStatisticsLogic()

    # segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    # segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterVolumeNode.GetID())
    # segStatLogic.getParameterNode().SetParameter("visibleSegmentsOnly", "False")

    # segStatLogic.computeStatistics()

    # # Export results to table (just to see all results)
    # resultsTableNode = slicer.vtkMRMLTableNode()
    # slicer.mrmlScene.AddNode(resultsTableNode)
    # segStatLogic.exportToTable(resultsTableNode)
    # segStatLogic.showTable(resultsTableNode)

    # self.delayDisplay("Check a few numerical results")

    # stats = segStatLogic.getStatistics()
    # self.assertEqual( round(stats['Tumor', 'LabelmapSegmentStatisticsPlugin.volume_mm3']), 19498.0)

    self.delayDisplay('test_Engrave1 passed')
