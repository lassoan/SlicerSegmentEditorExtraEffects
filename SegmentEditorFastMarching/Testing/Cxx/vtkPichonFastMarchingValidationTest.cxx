#include "vtkPichonFastMarchingTestUtilities.h"

#include <functional>
#include <limits>

int vtkPichonFastMarchingValidationTest(int, char*[])
{
  using namespace FastMarchingTest;
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const double infinity = std::numeric_limits<double>::infinity();
  const int maximum = std::numeric_limits<int>::max();

  using InvalidInitialization = std::function<void(vtkPichonFastMarching*)>;
  const InvalidInitialization invalidInitializations[] = {
    [](auto* filter) { filter->init(0, 32, 32, 8, 1, 1, 1); },
    [](auto* filter) { filter->init(6, 32, 32, 8, 1, 1, 1); },
    [maximum](auto* filter) { filter->init(maximum, maximum, maximum, 8, 1, 1, 1); },
    [](auto* filter) { filter->init(32, 32, 32, -1, 1, 1, 1); },
    [nan](auto* filter) { filter->init(32, 32, 32, nan, 1, 1, 1); },
    [infinity](auto* filter) { filter->init(32, 32, 32, infinity, 1, 1, 1); },
    [maximum](auto* filter) { filter->init(32, 32, 32, maximum, 1, 1, 1); },
    [](auto* filter) { filter->init(32, 32, 32, 8, 0, 1, 1); },
    [](auto* filter) { filter->init(32, 32, 32, 8, -1, 1, 1); },
    [nan](auto* filter) { filter->init(32, 32, 32, 8, 1, nan, 1); },
    [infinity](auto* filter) { filter->init(32, 32, 32, 8, 1, 1, infinity); },
    [](auto* filter) { filter->init(32, 32, 32, 8, 1e-300, 1, 1); },
  };
  for (const auto& initialize : invalidInitializations)
    {
    vtkNew<vtkPichonFastMarching> filter;
    vtkNew<EventCounter> events;
    filter->AddObserver(vtkCommand::ErrorEvent, events);
    initialize(filter);
    CHECK(events->Errors > 0);
    CHECK(filter->nValidSeeds() == 0);
    }

  using InvalidInput = std::function<void(vtkImageData*)>;
  const InvalidInput invalidInputs[] = {
    [](auto* image) { image->AllocateScalars(VTK_FLOAT, 1); },
    [](auto* image) { image->AllocateScalars(VTK_SHORT, 2); },
    [](auto* image) { image->GetPointData()->SetScalars(nullptr); },
    [](auto* image) { image->GetPointData()->GetScalars()->SetNumberOfTuples(1); },
    [](auto* image) { image->SetExtent(1, 32, 0, 31, 0, 31); },
    [](auto* image) { image->SetDimensions(24, 24, 24); },
    [](auto* image) { *static_cast<short*>(image->GetScalarPointer(16, 16, 16)) = -1; },
    [](auto* image) { *static_cast<short*>(image->GetScalarPointer(16, 16, 16)) = 9; },
  };
  for (const auto& invalidate : invalidInputs)
    {
    auto source = Source();
    vtkNew<vtkPichonFastMarching> filter;
    vtkNew<EventCounter> events;
    filter->AddObserver(vtkCommand::ErrorEvent, events);
    Configure(filter, source);
    invalidate(source);
    filter->setNPointsEvolution(0);
    filter->Update();
    CHECK(events->Errors > 0);
    }

  auto source = Source();
  for (int mismatch = 0; mismatch < 3; ++mismatch)
    {
    vtkNew<vtkPichonFastMarching> filter;
    vtkNew<EventCounter> events;
    filter->AddObserver(vtkCommand::ErrorEvent, events);
    Configure(filter, source);
    auto seeds = Output(source);
    if (mismatch == 0)
      seeds->AllocateScalars(VTK_FLOAT, 1);
    else if (mismatch == 1)
      seeds->AllocateScalars(VTK_SHORT, 2);
    else
      seeds->GetPointData()->SetScalars(nullptr);
    CHECK(filter->addSeedsFromImage(seeds) == 0);
    CHECK(events->Errors > 0);
    CHECK(filter->nValidSeeds() == 0);
    }

  for (int mismatch = 0; mismatch < 3; ++mismatch)
    {
    vtkNew<vtkPichonFastMarching> filter;
    vtkNew<EventCounter> events;
    filter->AddObserver(vtkCommand::ErrorEvent, events);
    Configure(filter, source);
    auto output = Output(source);
    if (mismatch == 0)
      output->AllocateScalars(VTK_UNSIGNED_SHORT, 1);
    else if (mismatch == 1)
      output->AllocateScalars(VTK_SHORT, 2);
    else
      output->GetPointData()->GetScalars()->SetNumberOfTuples(1);
    output->GetPointData()->GetScalars()->Fill(7);
    vtkSmartPointer<vtkDataArray> original = output->GetPointData()->GetScalars();
    filter->SetOutput(output);
    filter->setNPointsEvolution(0);
    filter->Update();
    CHECK(events->Errors > 0);
    CHECK(output->GetPointData()->GetScalars() == original);
    CHECK(original->GetComponent(0, 0) == 7);
    }

  vtkNew<vtkPichonFastMarching> guarded;
  vtkNew<EventCounter> events;
  guarded->AddObserver(vtkCommand::ErrorEvent, events);
  Configure(guarded, source);
  guarded->initNewExpansion();
  CHECK(events->Errors > 0);
  Configure(guarded, source);
  events->Errors = 0;
  guarded->show(1.0);
  CHECK(events->Errors == 0);
  guarded->setNPointsEvolution(100);
  guarded->Update();
  CHECK(events->Errors > 0);
  CHECK(guarded->nKnownPoints() == 0);
  return EXIT_SUCCESS;
}
