cmake_minimum_required(VERSION 3.5)

project(SegmentEditorExtraEffects)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/lassoan/SlicerSegmentEditorExtraEffects")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Andras Lasso (PerkLab, Queen's), Kyle MacNeil (Med-i Lab, Queen's; SPL, BWH), Andrey Fedorov (SPL, BWH)")
set(EXTENSION_DESCRIPTION "Experimental effects for Segment Editor")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/lassoan/SlicerSegmentEditorExtraEffects/master/SegmentEditorExtraEffects.png")
set(EXTENSION_SCREENSHOTURLS "\
https://raw.githubusercontent.com/lassoan/SlicerSegmentEditorExtraEffects/master/FastMarchingInput.png \
https://raw.githubusercontent.com/lassoan/SlicerSegmentEditorExtraEffects/master/FastMarchingOutput.png \
https://raw.githubusercontent.com/lassoan/SlicerSegmentEditorExtraEffects/master/WatershedOutput.png \
")
set(EXTENSION_DEPENDS "MarkupsToModel") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SegmentEditorFastMarching)
add_subdirectory(SegmentEditorFloodFilling)
add_subdirectory(SegmentEditorMaskVolume)
add_subdirectory(SegmentEditorSurfaceCut)
add_subdirectory(SegmentEditorWatershed)
add_subdirectory(SegmentEditorDrawTube)
add_subdirectory(SegmentEditorCropSegment)
IF (Slicer_VERSION VERSION_LESS 4.9)
  # Slicer 4.9 and above has Hollow effect built in
  add_subdirectory(SegmentEditorHollow)
ENDIF()
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
