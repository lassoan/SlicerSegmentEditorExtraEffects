#include "vtkPichonFastMarchingTestUtilities.h"

int vtkPichonFastMarchingExhaustionTest(int, char*[])
{
  using namespace FastMarchingTest;
  auto source = Source(8);
  vtkNew<vtkPichonFastMarching> filter;
  Configure(filter, source);
  filter->SetOutput(Output(source));
  filter->setNPointsEvolution(0);
  filter->Update();
  vtkNew<EventCounter> events;
  filter->AddObserver(vtkCommand::ProgressEvent, events);
  filter->AddObserver(vtkCommand::ErrorEvent, events);
  CHECK(filter->addSeedIJK(3, 3, 3) == 1);
  filter->setNPointsEvolution(1000000);
  filter->Modified();
  filter->Update();
  filter->show(1.0);
  CHECK(filter->nKnownPoints() == 8);
  CHECK(Count(filter->GetOutput()) == 8);
  // Continuing the loop after its eight interior voxels emits all 20 progress steps.
  CHECK(events->Progress < GRANULARITY_PROGRESS);
  return EXIT_SUCCESS;
}
