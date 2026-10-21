#include "vtkPichonFastMarchingTestUtilities.h"

#include <vtkInformation.h>
#include <vtkObjectFactory.h>

namespace
{
class DirtyOutputFastMarching : public vtkPichonFastMarching
{
public:
  static DirtyOutputFastMarching* New();
  vtkTypeMacro(DirtyOutputFastMarching, vtkPichonFastMarching);
  int AllocationCount = 0;

protected:
  void AllocateOutputData(vtkImageData* output, vtkInformation* info, int* extent) override
  {
    this->Superclass::AllocateOutputData(output, info, extent);
    ++this->AllocationCount;
    output->GetPointData()->GetScalars()->Fill(123);
  }
};
vtkStandardNewMacro(DirtyOutputFastMarching);
}

int vtkPichonFastMarchingOutputTest(int, char*[])
{
  using namespace FastMarchingTest;
  auto source = Source();
  vtkNew<DirtyOutputFastMarching> filter;
  Configure(filter, source);
  filter->setNPointsEvolution(0);
  filter->Update();
  CHECK(filter->AllocationCount == 1);
  CHECK(Count(filter->GetOutput(), 0) == source->GetNumberOfPoints());

  // Supplied labels, even in a shared array, belong to the caller.
  for (bool shared : {false, true})
    {
    vtkNew<DirtyOutputFastMarching> supplied;
    Configure(supplied, source);
    auto output = Output(source);
    *static_cast<short*>(output->GetScalarPointer(16, 16, 16)) = 7;
    vtkSmartPointer<vtkDataArray> reference;
    if (shared)
      reference = output->GetPointData()->GetScalars();
    auto* scalars = output->GetPointData()->GetScalars();
    supplied->SetOutput(output);
    supplied->setNPointsEvolution(0);
    supplied->Update();
    CHECK(supplied->AllocationCount == 0);
    CHECK(supplied->GetOutput()->GetPointData()->GetScalars() == scalars);
    CHECK(Count(supplied->GetOutput(), 7) == 1);
    CHECK(Count(supplied->GetOutput(), 0) == source->GetNumberOfPoints() - 1);
    supplied->addSeedIJK(12, 12, 12);
    supplied->setNPointsEvolution(500);
    supplied->Update();
    supplied->show(1.0);
    CHECK(Count(supplied->GetOutput(), 1) > 1);
    CHECK(*static_cast<short*>(output->GetScalarPointer(16, 16, 16)) == 7);
    }
  return EXIT_SUCCESS;
}
