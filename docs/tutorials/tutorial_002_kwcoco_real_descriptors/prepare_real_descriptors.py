#!/usr/bin/env python3
"""
Script to chip images with associated descriptors in the dataset

Script to generate and chip kwcoco geowatch images and
Stores results in a manifest.json file that has image/desciptor pairs
with associated file paths.
"""
# Standard libraries
import numpy as np
import os
import json

# Kitware libraries
import kwcoco
import kwarray
import kwimage
import ubelt as ub
import kwutil

import scriptconfig as scfg


class PrepareRealDescriptorsConfig(scfg.DataConfig):
    # Define the file paths to store generated data
    coco_fpath = scfg.Value(None, help='input kwcoco file to create chips / descriptors for')
    out_chips_dpath = scfg.Value('./chipped_images', help='Path to output the chips and their descriptors')
    out_mainfest_fpath = scfg.Value('manifest.json', help='Path that references all output data')

    window_size = scfg.Value((128, 128), help='Size of the window for slicing the image')

    visual_channels = scfg.Value('r|g|b', help='Channels used to generate visual chips')
    descriptor_channels = scfg.Value('hidden_layers:128', help='Channels used to generate descriptors')

    @classmethod
    def main(cls, cmdline=1, **kwargs):
        """
        Example:
            >>> # xdoctest: +SKIP
            >>> from chip_hidden_layers import *  # NOQA
            >>> cmdline = 0
            >>> kwargs = dict()
            >>> cls = ChipHiddenLayersCLI
            >>> cls.main(cmdline=cmdline, **kwargs)
        """
        import rich
        import rich.markup
        config = cls.cli(cmdline=cmdline, data=kwargs, strict=True,
                         special_options=False)
        rich.print('config = ' + rich.markup.escape(ub.urepr(config, nl=1)))

        # Create the directory to store chipped images if it does not exist
        out_mainfest_fpath = ub.Path(config.out_mainfest_fpath)
        out_images_dpath = ub.Path(config.out_chips_dpath)
        out_images_dpath.ensuredir()

        # Instantiate the kwcoco.CocoDataset object from the loaded JSON data
        dset = kwcoco.CocoDataset.coerce(config.coco_fpath)

        # Define the dimensions of the window slider for image chips
        window = kwutil.Yaml.coerce(config.window_size)

        # Initialize list to store image/descriptor pairs for each chipped image
        rows = []

        visual_channels = kwcoco.FusedChannelSpec.coerce(config.visual_channels)
        descriptor_channels = kwcoco.FusedChannelSpec.coerce(config.descriptor_channels)

        # Outer loop for each image in dataset
        for image_id in dset.images():

            # Generate a coco_image class object from the data set using the image id
            coco_image = dset.coco_image(image_id)

            # input_image_path = coco_image.primary_image_filepath()
            # Debugging - display current image using matplotlib
            # plt.imshow(plt.imread(input_image_path))
            # plt.show()

            # Assign the various elements for processing
            delayed_rasters = coco_image.imdelay()
            channels = delayed_rasters.channels

            if channels.intersection(visual_channels).numel() == 3:
                delayed_rgb = delayed_rasters.take_channels(visual_channels)
            else:
                print('warning: no rgb in data, falling back on first 3')
                delayed_rgb = delayed_rasters.take_channels(channels[0:3])

            if channels.intersection(descriptor_channels).numel() == 128:
                # select hidden_layers channels
                hidden_channels = descriptor_channels
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
                slice_path = out_images_dpath / suffix
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
        out_mainfest_fpath.parent.ensuredir()
        out_mainfest_fpath.write_text(json.dumps(tables, indent="    "))

        print(f"Manifest JSON file written to : {out_mainfest_fpath}")


__cli__ = PrepareRealDescriptorsConfig


if __name__ == '__main__':
    """

    CommandLine:
        python ~/code/smqtk-repos/SMQTK-IQR/docs/tutorials/chip_hidden_layers.py
        python -m chip_hidden_layers
    """
    __cli__.main()
