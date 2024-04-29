#Script to chip images and create associated descriptors.
# commet to see if git status is working

# Standard libraries
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# Kitware specific librareis
import kwcoco
import kwarray
import kwimage
import kwplot
import ubelt as ub


# Define the file paths to be same as tutorial script
DATA_FPATH = "../../demodata/vidshapes_rgb_data/data.kwcoco.json"
CHIPPED_IMAGES_FPATH = "../../demodata/chipped"

# Create directories if they don't exist
# os.makedirs(DATA_FPATH, exist_ok=True)
# os.makedirs(DVC_CHIPPED_DPATH, exist_ok=True)

# Check file path
print("print the file path for the data to chip: ", DATA_FPATH)
print("print the file path for chipped images: ", CHIPPED_IMAGES_FPATH)

# Declare dataset for chipped images
dset_chipped = kwcoco.CocoDataset()

# Load data for chipping
dset = kwcoco.CocoDataset.from_data(DATA_FPATH)

# Demo dataset
# dset_demo = kwcoco.CocoDataset.demo('vidshapes1')

#TO DO:  determine how to read off the number of images in a kwcoco dataset
for ii in range(5):

    # Pick an image, this is just an integer id value
    image_id = dset.images()[ii]

    # generate a coco_image class object from the data set using image id
    coco_image = dset.coco_image(image_id)

    # print the datatype of a coco_image, <class 'kwcoco.coco_image.CocoImage'>
    print("\n Coco image type: ",type(coco_image))

    # This is the path to img_00001.png
    input_image_path = coco_image.primary_image_filepath()

    # print the primary_image_filepath this is  <class 'ubelt.util_path.Path'>
    print("\n Coco primary_image_filepath: ", input_image_path, type(input_image_path), '\n')

    # To display this image, need to use the bash shell command - dont know why
    # result = ub.cmd(f'kwplot imshow {input_image_path}', verbose=3, shell=True)

    # Display using matplotlib, need to read the image from the file path
    # plt.imshow(plt.imread(input_image_path))
    # plt.show()


    # This method converts the image to a  <class 'numpy.ndarray'>
    # The image is 600x600 pixels with three channels, rgb
    input_image = coco_image.imdelay('r|g|b').finalize()

    print("Shape of RGB np.array image: ", np.shape(input_image), '\n')

    annotations = coco_image.annots()

    # looks like this image has 2 annotations based upon output
    print("Annotations: ", annotations, "type is: ", type(annotations),'\n')

    # capture location/dimension for the 2 annotations in this image
    annot_boxes = kwimage.Boxes(annotations.lookup('bbox'), 'xywh')

    # This shows the dimensions for each (2 in this example) annotation boxes
    print("What are annot_boxes?", annot_boxes, type(annot_boxes))

    annot_cat_ids = np.array(annotations.lookup('category_id'))

    shape = input_image.shape[0:2] # captures the first 2 dimensions, not the channels
    print("shape variable is: ", shape)

    # set the window for the slider
    window = (256, 256)

    # set the slider args base upon image shape and window size.
    slider = kwarray.SlidingWindow(shape, window, allow_overshoot=True)

    # TODO: this needs to have a consistent ordering if the descriptors
    # are used with other toy datasets
    # Categories are the names for annotated objects
    categories = dset.object_categories()

    print("\n Categories are : ", categories, type(categories), '\n')

    descriptor_dims = len(categories) * 2

    print("descriptor_dims is: ", descriptor_dims, type(descriptor_dims), '\n')

    # For loop using ub.ProgIter - can't see what the max index is??
    # index hooks in slider parameters and defines the slicing window
    for index in ub.ProgIter(slider, desc='sliding a window', verbose=3):

        # Slice out the relevant part of the image using the slider function
        # The index performs the slicer operation on the
        # first two dimensions (size of the image)
        part_image = input_image[index]

        # For debugging, view each window of the image
        # plt.imshow(part_image)
        # plt.show()

        print("Part image shape is: ", np.shape(part_image))

        print("The index in this loop: ", index)

        # Get a box corresponding to the slice (so we can use its helper methods)
        # Box captures an area of the original image
        # defined by (x1, y1, x2, y2), most likely
        box = kwimage.Box.from_slice(index)

        print('\n', "What does a box look like? ", box, type(box), '\n')

        # Returns a non-zero number for each annotation that overlaps this sliding
        # window. This is not an efficient check, but it will work for now.

        # Intersection area of annotation boxes with current window
        # divided by the union of these areas.
        # in this example, only the 4th window has an annotation
        annot_overlaps = annot_boxes.ious(box.boxes)[:, 0]

        print("Does the annotation overlap?", annot_overlaps, type(annot_overlaps), '\n')

        overlapping_cat_ids = annot_cat_ids[annot_overlaps > 0]

        print("Category ids for annots that overlap the window: ", overlapping_cat_ids)

        # this just looks up the name
        overlapping_cat_names = dset.categories(overlapping_cat_ids).lookup('name')

        print("Overlapping category names: ", overlapping_cat_names, type(overlapping_cat_names), '\n')

        overlapping_cat_idxs = np.array([categories.node_to_idx[name] for name in overlapping_cat_names], dtype=int)

        print("Overlapping category indices: ", overlapping_cat_idxs, type(overlapping_cat_idxs), '\n')

        # Make a random descriptor, but add an indicator based on the visible
        # annotation categories.

        # Creates an array with 6 values (2 times the number of categories)
        part_descriptor = np.random.rand(descriptor_dims)

        # Assigns descriptor values to 100 where the category index is present
        part_descriptor[overlapping_cat_idxs] = 100

        print("Part descriptor: ", part_descriptor)

        # converts from (x1,y1), (x2, y2) dimensions to xywh
        x, y, w, h = box.to_xywh().data

        print("output of box.to_xywh: ", box, "(", x, y, w, h, ")", '\n')


        suffix = f'img_{image_id:05d}-xywh={x:04d}_{y:04d}_{w:03d}_{h:03d}.png'


        print("suffix is: ", suffix, '\n')

        slice_path = "../../demodata/chipped_images/" + suffix
        print(f'slice_path={slice_path}\n')

        slice_desc_path = str(slice_path)[:-4] + "_desc.json"

        print(f'slice_desc_path={slice_desc_path}')

        kwimage.imwrite(slice_path, part_image)

        # Convert the NumPy array to a Python list
        part_descriptor_list = part_descriptor.tolist()

        # Save the list to the JSON file
        with open(slice_desc_path, 'w') as json_file:
            json.dump(part_descriptor_list, json_file)
