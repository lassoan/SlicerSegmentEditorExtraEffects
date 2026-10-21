set(KIT vtkSlicerSegmentEditorFastMarchingModuleLogic)

slicerMacroConfigureModuleCxxTestDriver(
  NAME ${KIT}
  SOURCES
    vtkPichonFastMarchingOutputTest.cxx
    vtkPichonFastMarchingLifecycleTest.cxx
    vtkPichonFastMarchingSeedImageTest.cxx
    vtkPichonFastMarchingValidationTest.cxx
    vtkPichonFastMarchingExhaustionTest.cxx
    vtkPichonFastMarchingPDFTest.cxx
  INCLUDE_DIRECTORIES
    ${MRMLCore_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/../../Logic
    ${CMAKE_CURRENT_BINARY_DIR}/../../Logic
  WITH_VTK_DEBUG_LEAKS_CHECK
  )

# The histogram helper is private to the logic library and is not exported.
target_sources(${KIT}CxxTests PRIVATE ../../Logic/vtkPichonFastMarchingPDF.cxx)

simple_test(vtkPichonFastMarchingOutputTest)
simple_test(vtkPichonFastMarchingLifecycleTest)
simple_test(vtkPichonFastMarchingSeedImageTest)
simple_test(vtkPichonFastMarchingValidationTest)
simple_test(vtkPichonFastMarchingExhaustionTest)
simple_test(vtkPichonFastMarchingPDFTest)
