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
- Local Threshold: fill segment in a selected region based on master volume intensity range. CTRL + left click adds the selected island within the threshold to the segment. The feature size, ROI, and fill method can be changed to prevent leaks into other structures.
