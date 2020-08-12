# SlicerSegmentEditorExtraEffects

Experimental effects for Segment Editor in 3D Slicer. These effects are kept here insted of distributed with Slicer because it is not yet clear if they are as good or better than existing effects or they are still in development and we want to allow more frequent updates.

- Draw Tube: segment tubular structures, such as catheters, nerves, vessels, by clicking on a few points along the path
- Engrave: draw text on segments using engraving or embossing
- Fast Marching: grow complete segmentation from the current segment; only one segment is supported at once, leaking out is controlled by adjustable target volume
- Flood Filling: add to the current segment all similar intensity voxels near the clicked position
- Mask Volume: fill a scalar volume with constant value inside/outside the selected segment
- Split Volume: extract pieces from a scalar volume around each segment and put them into separate scalar volumes (useful for createing multiple volumes from a scan that contains multiple specimens)
- Surface Cut: define a smooth 3D blob by specifying points on its surface (useful for quick approximate segmentation of convex objects)
- Watershed: Create complete segmentation from seeds, similarly to "Grow from seeds" effect in Slicer core. Advantage is that this effect can enforce smooth surfaces, thereby preventing leaks and reducing the need for additional smoothing after region growing. Disadvantage is that this effect recomputes the complete segmentation after any seed is changed, therefore it is significantly slower.
- Local Threshold: fill segment in a selected region based on master volume intensity range. CTRL/CMD + left click adds the selected island within the threshold to the segment. 

  The histogram represents the voxel intensities within the selected region of the image. The red lines on the left and right represent the minimum and maximum voxel intensities in the selected region, while the the the yellow line represents the average intensity. The yellow highlight underneath the histogram shows the current threshold range.

  Clicking and dragging on the histogram will let you manually specify the minimum/maximum intensities. The average then becomes the median intensity between the two. Right clicking on the histogram will cancel the manual selection.

  ![Labelled local threshold histogram](LocalThresholdHistogram.png)

  If you would like finer control over the threshold range, the threshold range slider can be used without, or in conjunction with the histogram to specify the range.

  The feature size, ROI, and fill method can be changed to prevent leaks into other structures. The required feature size depends on the structure being segmented. A larger feature sizes will prevent leaking through regions that are smaller than the feature size, however for thin structures, a feature size that is larger than the thinnest regions will result in the branches being truncated.
  
