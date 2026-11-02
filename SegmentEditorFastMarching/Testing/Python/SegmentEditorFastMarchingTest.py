import unittest

import numpy as np
import slicer
from vtk.util.numpy_support import vtk_to_numpy


def sourceArray():
  return (np.indices((32, 32, 32)).sum(axis=0) % 9).astype(np.int16)


def seedArray():
  seeds = np.zeros((32, 32, 32), dtype=np.int16)
  seeds[15:18, 15:18, 15:18] = 1
  return seeds


def arrayFromImage(image):
  return vtk_to_numpy(image.GetPointData().GetScalars()).reshape(image.GetDimensions()[::-1]).copy()


class FastMarchingEffectTest(unittest.TestCase):

  def setUp(self):
    slicer.mrmlScene.Clear(0)
    self.volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    slicer.util.updateVolumeFromArray(self.volume, sourceArray())
    self.volume.SetSpacing(0.7, 0.9, 1.3)
    self.segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    self.segmentation.CreateDefaultDisplayNodes()
    self.segmentation.SetReferenceImageGeometryParameterFromVolumeNode(self.volume)
    self.segmentId = self.segmentation.GetSegmentation().AddEmptySegment("Seeds")
    self.seeds = seedArray()
    slicer.util.updateSegmentBinaryLabelmapFromArray(
      self.seeds, self.segmentation, self.segmentId, self.volume)
    self.parameterNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    self.editor = slicer.qMRMLSegmentEditorWidget()
    self.editor.setMRMLScene(slicer.mrmlScene)
    self.editor.setMRMLSegmentEditorNode(self.parameterNode)
    self.editor.setSegmentationNode(self.segmentation)
    self.editor.setSourceVolumeNode(self.volume)
    self.editor.setCurrentSegmentID(self.segmentId)
    self.editor.setUndoEnabled(True)
    self.editor.setActiveEffectByName("Fast Marching")
    self.assertIsNotNone(self.editor.activeEffect())
    self.effect = self.editor.activeEffect().self()
    self.effect.percentMax.value = 10
    # Exercise the initial preview without an additional slider-change update.
    self.effect.marcher.value = 100

  def tearDown(self):
    self.editor.setActiveEffectByName("")
    self.editor.setMRMLSegmentEditorNode(None)
    self.editor.setMRMLScene(None)
    self.editor.deleteLater()
    slicer.mrmlScene.Clear(0)

  def segmentArray(self):
    return slicer.util.arrayFromSegmentBinaryLabelmap(
      self.segmentation, self.segmentId, self.volume).copy()

  def assertValidGrowth(self):
    output = arrayFromImage(self.effect.fm.GetOutput())
    self.assertTrue(np.isin(output, (0, 1)).all())
    grown = self.segmentArray()
    np.testing.assert_array_equal(output, grown)
    self.assertGreater(np.count_nonzero(grown), np.count_nonzero(self.seeds))
    self.assertTrue((grown[self.seeds != 0] == 1).all())
    return grown

  def test_repeatInitializeCancelApplyUndo(self):
    self.effect.onMarch()
    expected = self.assertValidGrowth()

    for repetition in range(3):
      with self.subTest(repetition=repetition):
        self.effect.onMarch()
        np.testing.assert_array_equal(self.assertValidGrowth(), expected)

        self.effect.marcher.value = 25
        reduced = self.segmentArray()
        self.assertGreater(np.count_nonzero(reduced), 0)
        self.assertLess(np.count_nonzero(reduced), np.count_nonzero(expected))
        self.assertTrue((reduced <= expected).all())
        self.effect.marcher.value = 100
        np.testing.assert_array_equal(self.segmentArray(), expected)

        self.effect.onCancel()
        self.assertIsNone(self.effect.fm)
        np.testing.assert_array_equal(self.segmentArray(), self.seeds)
        self.effect.onMarch()
        np.testing.assert_array_equal(self.assertValidGrowth(), expected)

        self.effect.onApply()
        self.assertIsNone(self.editor.activeEffect())
        np.testing.assert_array_equal(self.segmentArray(), expected)
        self.editor.undo()
        np.testing.assert_array_equal(self.segmentArray(), self.seeds)

        self.editor.setActiveEffectByName("Fast Marching")
        self.effect = self.editor.activeEffect().self()
        self.effect.onMarch()
        np.testing.assert_array_equal(self.assertValidGrowth(), expected)
