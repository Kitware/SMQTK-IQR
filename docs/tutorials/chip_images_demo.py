# Script to generate and chip kwcoco geowatch images and
# create associated 'dummy' descriptors.
# Stores results in a manifest.json file that has image/desciptor pairs
# with associated file paths.

# Standard libraries
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# Kitware libraries
import kwcoco
import kwarray
import kwimage
import kwplot
import ubelt as ub

# Define the file paths to store generated data
DATA_FPATH = ub.Path("../../demodata/vidshapes_rgb_data/data.kwcoco.json")
DEMODATA_OUTPUT_PATH = ub.Path("../../demodata").absolute().resolve()
CHIPPED_IMAGES_DPATH = DEMODATA_OUTPUT_PATH / "chipped"
OUTPUT_FPATH = DEMODATA_OUTPUT_PATH / "manifest.json"

# Create the directory to store chipped images if it does not exist
CHIPPED_IMAGES_DPATH.ensuredir()

# Define the dimensions of the window slider for image chips
window = (256, 256)
frames = 20
num_videos = 1

# Generate kwcoco Dataset
dset = kwcoco.CocoDataset.demo(
    "vidshapes", num_frames=frames, num_videos=num_videos, background="amazon"
)

# Initialize list to store image/descriptor pairs for each chipped image
rows = []

# Outer loop for each image in dataset
for ii in range(dset.n_images):

    # Select image for slicing/chipping
    image_id = dset.images()[ii]

    # Generate a coco_image class object from the data set using the image id
    coco_image = dset.coco_image(image_id)

    input_image_path = coco_image.primary_image_filepath()

    # Debugging - display current image using matplotlib
    # plt.imshow(plt.imread(input_image_path))
    # plt.show()

    # This method converts the image to a  <class 'numpy.ndarray'>
    # The default image is 600x600 pixels with three channels, rgb
    input_image = coco_image.imdelay("r|g|b").finalize()

    # First 2 elements of image are dimensions, don't need channel info
    shape = input_image.shape[0:2]

    # Capture location (boxes), ids and names for annotations in image
    # These are extracted from the coco_image object
    annotations = coco_image.annots()
    annot_boxes = kwimage.Boxes(annotations.lookup("bbox"), "xywh")
    annot_cat_ids = np.array(annotations.lookup("category_id"))
    annot_cat_names = dset.categories(annot_cat_ids).lookup("name")
    print(f"Annotation ids: {annot_cat_ids} and names: {annot_cat_names}", "\n")

    # Set the slider args base upon image shape and window size.
    slider = kwarray.SlidingWindow(shape, window, allow_overshoot=True)
    # print("\n slider params: ", slider, '\n')

    # TODO: this needs to have a consistent ordering if the descriptors
    # are used with other toy datasets

    # Define the number of descriptor dimensions from number of categories
    categories = dset.object_categories()
    descriptor_dims = len(categories) * 2

    # Chipping/slicing loop using ub.ProgIter and slider args.
    for index in ub.ProgIter(slider, desc="sliding a window", verbose=3):

        # Slice out the relevant part of the image using the slider function
        # The index performs the slicer operation on the
        # first two dimensions of image
        part_image = input_image[index]

        # Debugging - view each window of the image
        # plt.imshow(part_image)
        # plt.show()

        # Get a box corresponding to the slice to use 'box' methods
        # Box captures an area of the original image
        # defined by positionts (x1, y1, x2, y2)
        box = kwimage.Box.from_slice(index)

        # Capture intersection area of annotation boxes with current window
        # divided by the union of these areas using ious() method
        annot_overlaps = annot_boxes.ious(box.boxes)[:, 0]

        # Capture annotation category ids that overlap with current window
        overlapping_cat_ids = annot_cat_ids[annot_overlaps > 0]
        # print("Annotations that overlap: ", annot_overlaps, overlapping_cat_ids, '\n')

        # Look up name of annotation category ids
        # Extract cateory ids -> name -> index and convert to numpy array
        overlapping_cat_names = dset.categories(overlapping_cat_ids).lookup("name")
        overlapping_cat_idxs = np.array(
            [categories.node_to_idx[name] for name in overlapping_cat_names], dtype=int
        )

        # Generate descriptor with random values
        part_descriptor = np.random.rand(descriptor_dims)

        # Modify descriptor values to 100 where the category index is present
        part_descriptor[overlapping_cat_idxs] = 100

        # Converts from (x1,y1), (x2, y2) dimensions to xywh
        x, y, w, h = box.to_xywh().data
        # print("output of box.to_xywh: ", box, "(", x, y, w, h, ")", '\n')

        # Generate file paths
        suffix = f"img_{image_id:05d}-xywh={x:04d}_{y:04d}_{w:03d}_{h:03d}.png"
        slice_path = CHIPPED_IMAGES_DPATH / suffix
        slice_desc_path = slice_path.augment(stemsuffix="_desc", ext=".json")

        # Save image chip/slice to the path defined above
        kwimage.imwrite(slice_path, part_image)

        # Convert the NumPy array to a Python list
        part_descriptor_list = part_descriptor.tolist()

        # Save the list to the JSON file
        with open(slice_desc_path, "w") as json_file:
            json.dump(part_descriptor_list, json_file)

        # Append to outer loop list
        row = {
            "image_path": os.fspath(slice_path),
            "desc_path": os.fspath(slice_desc_path),
        }
        rows.append(row)

tables = {"Image_Descriptor_Pairs": rows}
OUTPUT_FPATH.write_text(json.dumps(tables, indent="    "))
