import os
import qt, slicer
from slicer.ScriptedLoadableModule import *

class SegmentEditorLocalThreshold(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SegmentEditorLocalThreshold"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = ["Segmentations"]
    self.parent.contributors = ["Kyle Sunderland (PerkLab, Queen's)", "Andras Lasso (PerkLab, Queen's)"]
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

class SegmentEditorLocalThresholdTest(ScriptedLoadableModuleTest):
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
