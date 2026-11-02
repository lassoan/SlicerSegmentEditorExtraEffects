#include "vtkPichonFastMarchingTestUtilities.h"

int vtkPichonFastMarchingSeedImageTest(int, char*[])
{
  using namespace FastMarchingTest;
  auto source = Source();
  std::vector<short> reference;
  for (int type : {VTK_SHORT, VTK_UNSIGNED_SHORT})
    {
    vtkNew<vtkPichonFastMarching> filter;
    Configure(filter, source);
    vtkNew<vtkImageData> seeds;
    seeds->SetExtent(15, 17, 15, 17, 15, 17);
    seeds->AllocateScalars(type, 1);
    seeds->GetPointData()->GetScalars()->Fill(type == VTK_SHORT ? 1 : 32768);
    CHECK(filter->addSeedsFromImage(seeds) == 27);
    CHECK(filter->nValidSeeds() == 27);
    filter->setNPointsEvolution(1000);
    filter->Update();
    filter->show(1.0);
    if (reference.empty())
      reference = Pixels(filter->GetOutput());
    else
      CHECK(Pixels(filter->GetOutput()) == reference);
    }
  vtkNew<vtkPichonFastMarching> explicitSeeds;
  Configure(explicitSeeds, source);
  for (int k = 15; k <= 17; ++k)
    for (int j = 15; j <= 17; ++j)
      for (int i = 15; i <= 17; ++i)
        explicitSeeds->addSeedIJK(i, j, k);
  explicitSeeds->setNPointsEvolution(1000);
  explicitSeeds->Update();
  explicitSeeds->show(1.0);
  CHECK(Pixels(explicitSeeds->GetOutput()) == reference);

  vtkNew<vtkPichonFastMarching> partial;
  Configure(partial, source);
  vtkNew<vtkImageData> seeds;
  seeds->SetExtent(-1, 2, 15, 15, 15, 15);
  seeds->AllocateScalars(VTK_SHORT, 1);
  seeds->GetPointData()->GetScalars()->Fill(1);
  CHECK(partial->addSeedsFromImage(seeds) == 2);
  CHECK(partial->nValidSeeds() == 2);
  return EXIT_SUCCESS;
}
