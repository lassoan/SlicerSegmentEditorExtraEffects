
#-----------------------------------------------------------------------------
set(MODULE_NAME SegmentEditorFastMarching)

# vtkPichonFastMarching used to be in Slicer core but it was moved
# to this extension in Slicer-4.13.
add_subdirectory(Logic)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ${MODULE_NAME}Lib/__init__.py
  ${MODULE_NAME}Lib/SegmentEditorEffect.py
  )

set(MODULE_PYTHON_RESOURCES
  ${MODULE_NAME}Lib/SegmentEditorEffect.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  add_subdirectory(Testing)
endif()
