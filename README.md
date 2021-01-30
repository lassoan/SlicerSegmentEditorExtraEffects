# SlicerSegmentEditorExtraEffects

Experimental effects for Segment Editor in 3D Slicer. These effects are kept here insted of distributed with Slicer because it is not yet clear if they are as good or better than existing effects or they are still in development and we want to allow more frequent updates.

## Draw Tube

Segment tubular structures, such as catheters, nerves, vessels, by clicking on a few points along the path.

## Engrave

Draw text on segments using engraving or embossing.

## Fast Marching

Grow complete segmentation from the current segment; only one segment is supported at once, leaking out is controlled by adjustable target volume.

## Flood Filling

Add to the current segment all similar intensity voxels near the clicked position. Generally "Local threshold" effect is recommended instead of this effect because this effect often either cannot prevent leaking into other structures or provides incomplete segmentation.

## Mask Volume

Fill a scalar volume with constant value inside/outside the selected segment.
The effect was moved to Slicer core in Slicer-4.13.

## Split Volume

Extract pieces from a scalar volume around each segment and put them into separate scalar volumes (useful for createing multiple volumes from a scan that contains multiple specimens).

## Surface Cut

Define a smooth 3D blob by specifying points on its surface. Useful for quick approximate segmentation of convex objects.

## Watershed

Create complete segmentation from seeds, similarly to "Grow from seeds" effect in Slicer core. Advantage of this effectis that it can enforce smooth surfaces, thereby preventing leaks and reducing the need for additional smoothing after region growing. Disadvantage is that this effect recomputes the complete segmentation after any seed is changed, therefore it is significantly slower.

## Local Threshold

Add the structure that is located at the selected position and has intensity values within the specified threshold range. Select a threshold range then Ctrl + left-click (on macOS Cmd + left-click) in a slice view to add the clicked region to the current segment. 

The threshold range can be set visually (based on the glowing color overlay) or based on a local histogram. The histogram represents voxel intensity distribution within a selected region of the image. Region can be selected by left-click and drag in any slice viewers. The red lines on the left and right represent the minimum and maximum voxel intensities in the selected region, while the orange line represents the average intensity. The yellow highlight underneath the histogram shows the currently set threshold range. Clicking and dragging on the histogram will let you manually specify the minimum/maximum intensities. The average then becomes the median intensity between the two. Right clicking on the histogram will cancel the manual selection.

![Labelled local threshold histogram](LocalThresholdHistogram.png)

For finer control over the threshold range, the threshold range slider can be used without, or in conjunction with the histogram to specify the range.

Minimum diameter, ROI (region of interest), and segmentation algorithm can be changed to limit how large surrounding is added to the segment. To add less to the segment, increase "Minimum diameter" value and/or specify a region of interest. A larger minimum diameter value will prevent leaking through regions that are smaller than that minimum size, however for thin structures, a minimum diameter that is larger than the thinnest regions will result in the branches being truncated.

To make the segmented structure smoother, choose Watershed algorithm and increase feature size.
