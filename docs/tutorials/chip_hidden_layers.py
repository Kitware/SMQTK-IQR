# Script to chip images with associated descriptors in the dataset

# Script to generate and chip kwcoco geowatch images and
# Stores results in a manifest.json file that has image/desciptor pairs
# with associated file paths.

# Need to navigate to folder containing the JSON file predict file

# $ cd /home/local/KHQ/paul.beasly/.cache/geowatch/tests/fusion/predict

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
import rich
import rich.markup
import kwutil


import scriptconfig as scfg

class DemoModelBuildCLI(scfg.DataConfig):
  DEMODATA_OUTPUT_PATH = str(ub.Path.appdir('smqtk/model_demo'))
  # Define the file paths to store generated data
  DATA_FPATH = "$HOME/.cache/geowatch/tests/fusion/predict/pred.kwcoco.json"
  window_size = scfg.Value((128, 128), help='Size of the window for slicing the image')

config = DemoModelBuildCLI.cli()

import rich
rich.print(rich.markup.escape(ub.urepr(config)))

config.DEMODATA_OUTPUT_PATH = ub.Path(config.DEMODATA_OUTPUT_PATH).ensuredir()
CHIPPED_IMAGES_DPATH = (config.DEMODATA_OUTPUT_PATH) / "chipped"
OUTPUT_FPATH = (config.DEMODATA_OUTPUT_PATH) / "manifest.json"

# Instantiate the kwcoco.CocoDataset object from the loaded JSON data
dset = kwcoco.CocoDataset(config.DATA_FPATH)

# Create the directory to store chipped images if it does not exist
CHIPPED_IMAGES_DPATH.ensuredir()

# Define the dimensions of the window slider for image chips
window = kwutil.Yaml.coerce(config.window_size)
frames = 9
num_videos = 1


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

    # Assign the various elements for processing
    delayed_rasters = coco_image.imdelay()
    channels = delayed_rasters.channels

    if channels.intersection('r|g|b').numel() == 3:
        delayed_rgb = delayed_rasters.take_channels("r|g|b")
    else:
        print('warning: no rgb in data, falling back on first 3')
        delayed_rgb = delayed_rasters.take_channels(channels[0:3])

    if channels.intersection(kwcoco.FusedChannelSpec.coerce('hidden_layers:128')).numel() == 128:
        # select hidden_layers channels
        hidden_channels = kwcoco.FusedChannelSpec.coerce('hidden_layers:128')
    else:
        print('warning no hidden layers in data, falling back on last 128')
        hidden_channels = channels[-128:]

    delayed_descriptors = delayed_rasters.take_channels(hidden_channels)

    # Capture shape of the image
    # TODO: there might be a cleaner way to do this
    shape = (delayed_rgb.finalize()).shape[0:2]

    # Set the slider args base upon image shape and window size.
    slider = kwarray.SlidingWindow(shape, window, allow_overshoot=True)
    # print("\n slider params: ", slider, '\n')

    # TODO: this needs to have a consistent ordering if the descriptors
    # are used with other toy datasets

    # Define the number of descriptor dimensions from number of categories
    # categories = dset.object_categories()
    # descriptor_dims = len(categories) * 2

    # Chipping/slicing loop using ub.ProgIter and slider args.
    for index in ub.ProgIter(slider, desc="sliding a window", verbose=3):

        # Slice out the relevant part of the image using the slider function
        # The index performs the slicer operation on the
        # first two dimensions of image
        delayed_part_image = delayed_rgb[index]
        delayed_part_descriptor = delayed_descriptors[index]
        part_image = delayed_part_image.finalize()
        part_descriptor = delayed_part_descriptor.finalize()

        part_image = kwarray.robust_normalize(part_image)

        avg_part_descriptor = np.nanmean(part_descriptor, axis=(0, 1))

        # Debugging - view each window of the image
        # plt.imshow(part_image)
        # plt.show()

        # Get a box corresponding to the slice to use 'box' methods
        # Box captures an area of the original image
        # defined by positionts (x1, y1, x2, y2)
        box = kwimage.Box.from_slice(index)

        # Converts from (x1,y1), (x2, y2) dimensions to xywh
        x, y, w, h = box.to_xywh().data
        # print("output of box.to_xywh: ", box, "(", x, y, w, h, ")", '\n')

        # Generate file paths
        part_image = kwimage.ensure_uint255(part_image)
        suffix = f"img_{image_id:05d}-xywh={x:04d}_{y:04d}_{w:03d}_{h:03d}.png"
        slice_path = CHIPPED_IMAGES_DPATH / suffix
        slice_desc_path = slice_path.augment(stemsuffix="_desc", ext=".json")

        # Save image chip/slice to the path defined above
        #print(f'Write: {slice_path}')
        kwimage.imwrite(slice_path, part_image)

        # Convert the NumPy array to a Python list
        part_descriptor_list = avg_part_descriptor.tolist()

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

print(f"Manifest JSON file written to : {OUTPUT_FPATH}")
