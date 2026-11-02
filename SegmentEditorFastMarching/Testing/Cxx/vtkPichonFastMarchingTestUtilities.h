#ifndef vtkPichonFastMarchingTestUtilities_h
#define vtkPichonFastMarchingTestUtilities_h

#include "vtkPichonFastMarching.h"

#include <vtkDataArray.h>
#include <vtkCommand.h>
#include <vtkNew.h>
#include <vtkPointData.h>
#include <vtkSmartPointer.h>

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <vector>

#define CHECK(condition) \
  do \
    { \
    if (!(condition)) \
      { \
      std::cerr << __FILE__ << ":" << __LINE__ << ": " << #condition << std::endl; \
      return EXIT_FAILURE; \
      } \
    } while (false)

namespace FastMarchingTest
{
class EventCounter : public vtkCommand
{
public:
  static EventCounter* New() { return new EventCounter; }
  int Errors = 0;
  int Progress = 0;
  void Execute(vtkObject*, unsigned long event, void*) override
  {
    if (event == vtkCommand::ErrorEvent)
      ++this->Errors;
    else if (event == vtkCommand::ProgressEvent)
      ++this->Progress;
  }
};

inline vtkSmartPointer<vtkImageData> Source(int size = 32)
{
  auto image = vtkSmartPointer<vtkImageData>::New();
  image->SetDimensions(size, size, size);
  image->AllocateScalars(VTK_SHORT, 1);
  for (int k = 0; k < size; ++k)
    for (int j = 0; j < size; ++j)
      for (int i = 0; i < size; ++i)
        *static_cast<short*>(image->GetScalarPointer(i, j, k)) = (i + j + k) % 9;
  return image;
}

inline void Configure(vtkPichonFastMarching* filter, vtkImageData* source)
{
  int* dimensions = source->GetDimensions();
  double* spacing = source->GetSpacing();
  filter->SetInputData(source);
  filter->init(dimensions[0], dimensions[1], dimensions[2], 8,
    spacing[0], spacing[1], spacing[2]);
  filter->setActiveLabel(1);
}

inline vtkSmartPointer<vtkImageData> Output(vtkImageData* source)
{
  auto output = vtkSmartPointer<vtkImageData>::New();
  output->SetExtent(source->GetExtent());
  output->AllocateScalars(VTK_SHORT, 1);
  output->GetPointData()->GetScalars()->Fill(0);
  return output;
}

inline std::vector<short> Pixels(vtkImageData* image)
{
  const auto* data = static_cast<short*>(image->GetScalarPointer());
  return {data, data + image->GetNumberOfPoints()};
}

inline vtkIdType Count(vtkImageData* image, short label = 1)
{
  const auto values = Pixels(image);
  return std::count(values.begin(), values.end(), label);
}

inline void AddSeeds(vtkPichonFastMarching* filter, int center = 16)
{
  for (int k = center - 1; k <= center + 1; ++k)
    for (int j = center - 1; j <= center + 1; ++j)
      for (int i = center - 1; i <= center + 1; ++i)
        filter->addSeedIJK(i, j, k);
  filter->addSeedIJK(center, center, center);
  filter->addSeedIJK(center, center, center);
}

inline bool IsSubset(const std::vector<short>& smaller, const std::vector<short>& larger)
{
  if (smaller.size() != larger.size())
    return false;
  for (size_t i = 0; i < smaller.size(); ++i)
    if (smaller[i] != 0 && smaller[i] != larger[i])
      return false;
  return true;
}
}

#endif
