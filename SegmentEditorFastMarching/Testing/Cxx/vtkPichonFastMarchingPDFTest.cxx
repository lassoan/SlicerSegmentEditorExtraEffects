#include "vtkPichonFastMarchingTestUtilities.h"
#include "vtkPichonFastMarchingPDF.h"

#include <limits>
#include <stdexcept>

int vtkPichonFastMarchingPDFTest(int, char*[])
{
  PichonFastMarchingPDF pdf(8);
  pdf.smoothedBins[3] = 123;
  pdf.coefGauss[4] = 123;
  pdf.reset();
  CHECK(pdf.smoothedBins[3] == 0);
  CHECK(pdf.coefGauss[4] == 0);

  pdf.setUpdateRate(-1);
  pdf.addRealization(-1);
  pdf.addRealization(9);
  CHECK(pdf.toBeAdded.empty());
  CHECK(pdf.counter == 0);

  for (int depth : {-1, std::numeric_limits<int>::max()})
    {
    bool rejected = false;
    try
      {
      PichonFastMarchingPDF invalid(depth);
      }
    catch (const std::invalid_argument&)
      {
      rejected = true;
      }
    CHECK(rejected);
    }

  // Exercise both moment updates above the signed-int square limit.
  // Zero memory removes the sample before the quadratic smoothing loop.
  PichonFastMarchingPDF large(65535);
  large.setUpdateRate(-1);
  large.setMemory(0);
  large.addRealization(65535);
  large.update();
  CHECK(large.m1 == 0);
  CHECK(large.m2 == 0);
  CHECK(large.toBeAdded.empty());
  CHECK(large.inBins.empty());
  return EXIT_SUCCESS;
}
