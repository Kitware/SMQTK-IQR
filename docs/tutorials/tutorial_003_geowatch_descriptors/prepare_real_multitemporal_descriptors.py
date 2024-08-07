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


class PrepareRealMultiTemporalDescriptorsConfig(scfg.DataConfig):
    # Define the file paths to store generated data
    coco_fpath = scfg.Value(None, help='input kwcoco file to create chips / descriptors for')
    out_chips_dpath = scfg.Value('./chipped_images', help='Path to output the chips and their descriptors')
    out_mainfest_fpath = scfg.Value('manifest.json', help='Path that references all output data')

    space_window_size = scfg.Value((128, 128), help='Size of the window for slicing the image')
    time_window_size = scfg.Value(10, help='Number of frames per item')

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
        space_window = kwutil.Yaml.coerce(config.space_window_size)

        # Initialize list to store image/descriptor pairs for each chipped image
        rows = []

        visual_channels = kwcoco.FusedChannelSpec.coerce(config.visual_channels)
        descriptor_channels = kwcoco.FusedChannelSpec.coerce(config.descriptor_channels)

        time_window = (config.time_window_size,)

        all_videos = dset.videos()
        for video_id in all_videos:

            video = dset.index.videos[video_id]
            video_name = video['name']
            video_width = video['width']
            video_height = video['height']

            video_image_ids = list(dset.images(video_id=video_id))

            num_frames = len(video_image_ids)

            video_shape = (video_height, video_width)
            space_slider = kwarray.SlidingWindow(video_shape, space_window, allow_overshoot=True)

            time_slider = kwarray.SlidingWindow((num_frames,), time_window, allow_overshoot=True)

            for space_slice in space_slider:

                for time_slice in time_slider:
                    sub_image_ids = video_image_ids[time_slice[0]]

                    image_visual_stack = []
                    image_descriptor_stack = []

                    # Outer loop for each image in dataset
                    for image_id in sub_image_ids:

                        # Generate a coco_image class object from the data set using the image id
                        coco_image = dset.coco_image(image_id)

                        # Assign the various elements for processing
                        delayed_rasters = coco_image.imdelay(space='video')
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

                        # Slice out the relevant part of the image using the slider function
                        # The index performs the slicer operation on the
                        # first two dimensions of image
                        delayed_part_image = delayed_rgb[space_slice]
                        delayed_part_descriptor = delayed_descriptors[space_slice]
                        part_image = delayed_part_image.finalize()
                        part_descriptor = delayed_part_descriptor.finalize()

                        part_image = kwarray.robust_normalize(part_image)
                        part_image = kwimage.ensure_uint255(part_image)

                        frame_descriptor = np.nanmean(part_descriptor, axis=(0, 1))

                        image_visual_stack.append(part_image)
                        image_descriptor_stack.append(frame_descriptor)

                    sequence_descriptor = np.nanmean(np.stack(image_descriptor_stack), axis=0)

                    box = kwimage.Box.from_slice(space_slice)
                    x, y, w, h = box.to_xywh().data

                    time_start = time_slice[0].start
                    time_stop = time_slice[0].stop

                    # Generate file paths
                    suffix = f"{video_name}-xywh={x:04d}_{y:04d}_{w:03d}_{h:03d}-frames-{time_start}-{time_stop}.gif"
                    visual_fpath = out_images_dpath / suffix
                    descriptor_fpath = visual_fpath.augment(stemsuffix="_desc", ext=".json")

                    # Save image chip/slice to the path defined above
                    # kwimage.imwrite(visual_fpath, image_visual_stack[0], backend='pil')
                    # fpath, image_list = visual_fpath, image_visual_stack
                    pil_write_animated_gif(visual_fpath, image_visual_stack)

                    # Convert the NumPy array to a Python list
                    part_descriptor_list = sequence_descriptor.tolist()

                    # Save the list to the JSON file
                    with open(descriptor_fpath, "w") as json_file:
                        json.dump(part_descriptor_list, json_file)

                    # Append to outer loop list
                    row = {
                        "image_path": os.fspath(visual_fpath),
                        "desc_path": os.fspath(descriptor_fpath),
                    }
                    rows.append(row)

        tables = {"Image_Descriptor_Pairs": rows}
        out_mainfest_fpath.parent.ensuredir()
        out_mainfest_fpath.write_text(json.dumps(tables, indent="    "))

        print(f"Manifest JSON file written to : {out_mainfest_fpath}")


def pil_write_animated_gif(fpath, image_list):
    """
    References:
        https://imageio.readthedocs.io/en/v2.5.0/format_gif-pil.html
    """
    from PIL import Image
    pil_images = []
    for image in image_list:
        pil_img = Image.fromarray(image)
        pil_images.append(pil_img)
    pil_img.save(fpath)
    first_pil_img = pil_images[0]
    rest_pil_imgs = pil_images[1:]
    first_pil_img.save(fpath, save_all=True, append_images=rest_pil_imgs, optimize=False, fps=4, loop=0)


__cli__ = PrepareRealMultiTemporalDescriptorsConfig


if __name__ == '__main__':
    """

    CommandLine:
        python ~/code/smqtk-repos/SMQTK-IQR/docs/tutorials/chip_hidden_layers.py
        python -m chip_hidden_layers
    """
    __cli__.main()
