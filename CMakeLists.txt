cmake_minimum_required(VERSION 2.8.9)

project(SegmentEditorExtraEffects)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/SegmentEditorExtraEffects")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Andras Lasso (PerkLab, Queen's)")
set(EXTENSION_DESCRIPTION "Experimental effects for Segment Editor")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/SegmentEditorExtraEffects.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/SegmentEditorWatershed/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SegmentEditorWatershed)
add_subdirectory(SegmentEditorFastMarching)
add_subdirectory(SegmentEditorFloodFilling)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
