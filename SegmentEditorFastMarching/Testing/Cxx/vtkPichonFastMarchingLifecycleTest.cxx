#include "vtkPichonFastMarchingTestUtilities.h"

int vtkPichonFastMarchingLifecycleTest(int, char*[])
{
  using namespace FastMarchingTest;
  auto source = Source();
  vtkNew<vtkPichonFastMarching> filter;
  vtkNew<EventCounter> events;
  filter->AddObserver(vtkCommand::ErrorEvent, events);
  Configure(filter, source);
  AddSeeds(filter);
  CHECK(filter->nValidSeeds() == 29);
  filter->setNPointsEvolution(1000);
  filter->Update();
  filter->show(1.0);
  const auto full = Pixels(filter->GetOutput());
  CHECK(Count(filter->GetOutput()) > 27);
  CHECK(filter->nKnownPoints() > 27);
  CHECK(Count(filter->GetOutput(), 0) + Count(filter->GetOutput()) == source->GetNumberOfPoints());
  for (int k = 0; k < 32; ++k)
    for (int j = 0; j < 32; ++j)
      for (int i = 0; i < 32; ++i)
        if (i < BAND_OUT || j < BAND_OUT || k < BAND_OUT ||
            i >= 32 - BAND_OUT || j >= 32 - BAND_OUT || k >= 32 - BAND_OUT)
          CHECK(*static_cast<short*>(filter->GetOutput()->GetScalarPointer(i, j, k)) == 0);
  CHECK(*static_cast<short*>(filter->GetOutput()->GetScalarPointer(16, 16, 16)) == 1);

  filter->show(0.25);
  CHECK(Count(filter->GetOutput()) < std::count(full.begin(), full.end(), 1));
  CHECK(IsSubset(Pixels(filter->GetOutput()), full));
  filter->show(1.0);
  filter->Update();
  CHECK(Pixels(filter->GetOutput()) == full);

  // The caller may choose unit propagation distances for a nonunit image spacing.
  auto nonunitSource = Source();
  nonunitSource->SetSpacing(0.7, 1.2, 2.5);
  vtkNew<vtkPichonFastMarching> initialized;
  initialized->SetInputData(nonunitSource);
  initialized->init(32, 32, 32, 8, 1, 1, 1);
  initialized->setActiveLabel(1);
  // An optional setup-only Update must produce the same evolution.
  initialized->setNPointsEvolution(0);
  initialized->Update();
  AddSeeds(initialized);
  initialized->setNPointsEvolution(1000);
  initialized->Update();
  initialized->show(1.0);
  CHECK(Pixels(initialized->GetOutput()) == full);

  // Restarting an expansion discards pending seed observations.
  CHECK(filter->addSeedIJK(6, 6, 6) == 1);
  filter->initNewExpansion();
  initialized->initNewExpansion();
  CHECK(filter->nKnownPoints() == 0);
  CHECK(filter->nValidSeeds() > 0);
  filter->setNPointsEvolution(300);
  initialized->setNPointsEvolution(300);
  filter->Update();
  initialized->Update();
  filter->show(1.0);
  initialized->show(1.0);
  CHECK(Pixels(filter->GetOutput()) == Pixels(initialized->GetOutput()));
  CHECK(IsSubset(full, Pixels(filter->GetOutput())));
  CHECK(Count(filter->GetOutput()) > std::count(full.begin(), full.end(), 1));

  const auto expanded = Pixels(filter->GetOutput());
  filter->addSeedIJK(6, 6, 6);
  Configure(filter, source);
  CHECK(filter->nKnownPoints() == 0);
  CHECK(filter->nValidSeeds() == 0);
  filter->setNPointsEvolution(0);
  filter->Update();
  CHECK(Pixels(filter->GetOutput()) == expanded);

  // A fresh output starts empty, including after a change in dimensions.
  auto smaller = Source(24);
  vtkNew<vtkImageData> empty;
  filter->SetOutput(empty);
  Configure(filter, smaller);
  AddSeeds(filter, 12);
  filter->setNPointsEvolution(500);
  filter->Update();
  filter->show(1.0);
  vtkNew<vtkPichonFastMarching> fresh;
  Configure(fresh, smaller);
  AddSeeds(fresh, 12);
  fresh->setNPointsEvolution(500);
  fresh->Update();
  fresh->show(1.0);
  CHECK(filter->GetOutput()->GetNumberOfPoints() == smaller->GetNumberOfPoints());
  CHECK(Pixels(filter->GetOutput()) == Pixels(fresh->GetOutput()));
  CHECK(events->Errors == 0);
  return EXIT_SUCCESS;
}
