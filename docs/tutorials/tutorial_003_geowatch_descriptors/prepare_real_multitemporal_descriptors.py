#!/usr/bin/env python3
"""
Script to chip images with associated descriptors in the dataset

Script to generate and chip kwcoco geowatch images and
Stores results in a manifest.json file that has image/desciptor pairs
with associated file paths.

Requirements:
    pip install kwcoco kwgis kwutil scriptconfig geowatch
"""
import os
import scriptconfig as scfg
import ubelt as ub


class PrepareRealMultiTemporalDescriptorsConfig(scfg.DataConfig):
    # Define the file paths to store generated data
    coco_fpath = scfg.Value(None, help='input kwcoco file to create chips / descriptors for')
    out_chips_dpath = scfg.Value('./chipped_images', help='Path to output the chips / descriptors / metadata')

    out_mainfest_fpath = scfg.Value('manifest.json', help='Path that references all output data')

    space_window_size = scfg.Value((128, 128), help='Size of the window for slicing the image')
    time_window_size = scfg.Value(10, help='Number of frames per item')

    visual_channels = scfg.Value('r|g|b', help='Channels used to generate visual chips')
    descriptor_channels = scfg.Value('hidden_layers:128', help='Channels used to generate descriptors')
    normalize = scfg.Value(False, help='if True normalize the descriptor')

    method = scfg.Value('average', help='Can be average or center')

    use_annot_grid = scfg.Value(True, help='extract an irregular grid centered on annotations')
    use_generic_grid = scfg.Value(False, help='extract an regular grid across all videos / regions')

    workers = scfg.Value('auto', help='number of background workers')

    @classmethod
    def main(cls, cmdline=1, **kwargs):
        """
        Example:
            >>> # xdoctest: +SKIP
            >>> from chip_hidden_layers import *  # NOQA
            >>> cmdline = 0
            >>> kwargs = dict()
            >>> cls = PrepareRealMultiTemporalDescriptorsConfig
            >>> cls.main(cmdline=cmdline, **kwargs)
        """
        import rich
        import rich.markup
        config = cls.cli(cmdline=cmdline, data=kwargs, strict=True,
                         special_options=False)
        rich.print('config = ' + rich.markup.escape(ub.urepr(config, nl=1)))

        import json
        import kwarray
        import kwcoco
        import kwimage
        import kwutil
        from kwutil.util_progress import ProgressManager

        # Create the directory to store chipped images if it does not exist
        out_mainfest_fpath = ub.Path(config['out_mainfest_fpath']).absolute()
        out_images_dpath = ub.Path(config['out_chips_dpath']).absolute()
        out_images_dpath.ensuredir()

        # Instantiate the kwcoco.CocoDataset object from the loaded JSON data
        with ub.Timer('Loading kwcoco dataset'):
            dset = kwcoco.CocoDataset.coerce(config['coco_fpath'])

        # Define the dimensions of the window slider for image chips
        space_window = kwutil.Yaml.coerce(config['space_window_size'])

        # Initialize list to store image/descriptor pairs for each chipped image
        rows = []

        visual_channels = kwcoco.FusedChannelSpec.coerce(config['visual_channels'])
        descriptor_channels = kwcoco.FusedChannelSpec.coerce(config['descriptor_channels'])

        time_window = (config['time_window_size'],)

        pman = ProgressManager(backend='rich')

        workers = kwutil.coerce_num_workers(config['workers'])
        print(f'workers={workers}')
        jobs = ub.JobPool(mode='process', max_workers=workers)

        rich.print(f'Will write data to: [link={out_images_dpath}]{out_images_dpath}[/link]')

        with pman, jobs:
            all_videos = dset.videos()
            for video_id in pman.ProgIter(all_videos, desc='collect grid locations'):
                video = dset.index.videos[video_id]
                video_name = video['name']

                grid_locs = []
                if config['use_annot_grid']:
                    # Build irregular grid centered around annotations
                    annot_grid_locs = []
                    annots = dset.annots(video_id=video_id)
                    annot_track_ids = annots.lookup('track_id')
                    tid_to_aids = ub.group_items(annots, annot_track_ids)
                    for tid, aids in tid_to_aids.items():
                        track_annots = dset.annots(aids)
                        track_imgs = track_annots.images
                        det_boxes = []
                        for gid, aid in zip(track_imgs, track_annots):
                            coco_img = dset.coco_image(gid)
                            det = coco_img._detections_for_resolution(aids=[aid], space='video')
                            det.boxes
                            det_boxes.append(det.boxes)
                        boxes = kwimage.Boxes.concatenate(det_boxes)
                        space_slice = boxes.bounding_box().to_slices()[0]
                        sub_image_ids = list(track_imgs)
                        annot_grid_locs.append({
                            'space_slice': space_slice,
                            'sub_image_ids': sub_image_ids,
                            'video_id': video_id,
                        })
                    grid_locs += annot_grid_locs

                if config['use_generic_grid']:
                    # Build regular grid covering the entire spatial region
                    video_image_ids = list(dset.images(video_id=video_id))
                    num_frames = len(video_image_ids)
                    video_width = video['width']
                    video_height = video['height']
                    video_shape = (video_height, video_width)
                    space_slider = kwarray.SlidingWindow(video_shape, space_window, allow_overshoot=True)
                    time_slider = kwarray.SlidingWindow((num_frames,), time_window, allow_overshoot=True)
                    generic_grid_locs = []
                    for space_slice in space_slider:
                        for time_slice in time_slider:
                            sub_image_ids = video_image_ids[time_slice[0]]
                            generic_grid_locs.append({
                                'space_slice': space_slice,
                                'sub_image_ids': sub_image_ids,
                                'video_id': video_id,
                            })
                    grid_locs += generic_grid_locs

                # Submit all grid locations to be processed for this video to
                # the background workers.
                for grid_loc in  pman.ProgIter(grid_locs, desc=f'Submit jobs for {video_name}'):
                    sub_image_ids = grid_loc['sub_image_ids']
                    sub_images = dset.images(sub_image_ids)
                    coco_images = sub_images.coco_images
                    coco_images = [img.detach() for img in coco_images]

                    jobs.submit(build_location_descriptor,
                                grid_loc, coco_images, visual_channels,
                                descriptor_channels, out_images_dpath, config)

            for job in pman.ProgIter(jobs.as_completed(), total=len(jobs), desc='Collect process jobs'):
                row = job.result()
                if row is not None:
                    rows.append(row)

        tables = {"Image_Descriptor_Pairs": rows}
        out_mainfest_fpath.parent.ensuredir()
        out_mainfest_fpath.write_text(json.dumps(tables, indent="    "))

        print(f"Manifest JSON file written to : {out_mainfest_fpath}")
        rich.print(f'Wrote data to: [link={out_images_dpath}]{out_images_dpath}[/link]')


def build_location_descriptor(grid_loc, coco_images, visual_channels,
                              descriptor_channels, out_images_dpath, config):
    """
    Builds all information necessary to represent a specific spacetime volume
    """
    import geojson
    import json
    import kwimage
    import kwutil
    import pyproj
    import safer
    from geowatch.geoannots.geomodels import SiteModel, SiteHeader, Observation
    from kwgis.utils import util_gis
    from shapely.ops import transform
    space_slice = grid_loc['space_slice']
    frame_idxs = [g['frame_index'] for g in coco_images]
    frame_timestamps = [g['timestamp'] for g in coco_images]

    time_start = kwutil.datetime.coerce(frame_timestamps[0])
    time_stop = kwutil.datetime.coerce(frame_timestamps[-1])

    frame_start = frame_idxs[0]
    frame_stop = frame_idxs[-1]

    video = coco_images[0].video
    video_name = video['name']

    assert frame_start == min(frame_idxs)
    assert frame_stop == max(frame_idxs)

    try:
        image_visual_stack, sequence_descriptor = extract_spacetime_data(
            coco_images, space_slice, visual_channels,
            descriptor_channels, config)
    except Exception as ex:
        print(f'Issue for {grid_loc} ex={ex}')
    else:
        box = kwimage.Box.from_slice(space_slice).quantize().astype(int)
        x, y, w, h = box.to_xywh().data

        if 'wld_crs_info' in video:
            # Map the box back to crs84 if possible
            wld_crs_info = video['wld_crs_info']
            auth = wld_crs_info['auth']
            warp_vid_from_wld = kwimage.Affine.coerce(video['warp_wld_to_vid'])
            warp_wld_from_vid = warp_vid_from_wld.inv()
            wld_site_poly = box.to_polygon().warp(warp_wld_from_vid)

            crs = pyproj.CRS(':'.join(auth))
            crs84 = util_gis.get_crs84()
            project = pyproj.Transformer.from_crs(crs, crs84, always_xy=True).transform
            crs84_site_poly = transform(project, wld_site_poly.to_shapely())

            header = SiteHeader.empty()
            header['properties'].update(dict(
                start_date=time_start.date().isoformat(),
                end_date=time_stop.date().isoformat(),
                originator='smqtk-tutorial',
                status='unknown',
            ))
            # If the video has T&E properties with region-id information,
            # then we should include it.
            video_props = video.get('properties', {})
            if video_props:
                region_id = video_props.get('region_id', None)
                if region_id is not None:
                    header['properties']['region_id'] = region_id
            # TODO: get site-id if possible (requires knowing which annotation
            # this corresonds to if any).
            crs84_geometry = geojson.loads(geojson.dumps(crs84_site_poly))
            header['geometry'] = crs84_geometry
            header.infer_mgrs()
            header['properties'].setdefault('cache', {})
            header['properties']['cache'] = {
                'video_name': video['name'],
            }

            observations = []
            for coco_image in coco_images:
                obstime = coco_image.datetime
                # TODO: map to T&E sensor names?
                sensor = coco_image.get('sensor_coarse', None)
                obs = Observation(
                    properties={
                        'type': 'observation',
                        'observation_date': None,  # e.g. '2011-05-28',
                        'source': None,  # e.g. 'demosat-220110528T132754',
                        'sensor_name': sensor,  # e.g. 'demosat-2',
                        'current_phase': None,  # e.g. "No Activity".
                        'is_occluded': None,  # quirk / note: bool should be a string
                        'is_site_boundary': None,  # quirk / note: bool should be a string
                        'score': None,
                    },
                    geometry=None,
                )
                # TODO: next version of geowatch will have an empty property
                # obs = Observation.empty()
                obs['properties'].update({
                    'type': 'observation',
                    'observation_date': obstime.date().isoformat(),
                    'is_site_boundary': 'True',
                })
                obs['geometry'] = crs84_geometry
                observations.append(obs)

            model = SiteModel([header] + observations)
        else:
            model = None

        # Generate file paths
        suffix = f"{video_name}-xywh={x:04d}_{y:04d}_{w:03d}_{h:03d}-frames-{frame_start}-{frame_stop}.gif"
        visual_fpath = out_images_dpath / suffix
        descriptor_fpath = visual_fpath.augment(stemsuffix="_desc", ext=".json")

        if model is None:
            model_fpath = None
        else:
            model_fpath = visual_fpath.augment(stemsuffix="_site", ext=".geojson")

        # Save image chip/slice to the path defined above
        # kwimage.imwrite(visual_fpath, image_visual_stack[0], backend='pil')
        # fpath, image_list = visual_fpath, image_visual_stack
        pil_write_animated_gif(visual_fpath, image_visual_stack)

        # Convert the NumPy array to a Python list
        # if config.normalize:
        #     raise NotImplementedError

        part_descriptor_list = sequence_descriptor.tolist()

        # Save the list to the JSON file
        with safer.open(descriptor_fpath, "w", temp_file=not ub.WIN32) as json_file:
            json.dump(part_descriptor_list, json_file)

        if model_fpath is not None:
            with safer.open(model_fpath, "w", temp_file=not ub.WIN32) as model_file:
                model.dump(model_file)

        # Append to outer loop list
        row = {
            "image_path": os.fspath(visual_fpath),
            "desc_path": os.fspath(descriptor_fpath),
            "model_path": None if model_fpath is None else os.fspath(model_fpath),
        }
        return row


def extract_spacetime_data(coco_images, space_slice, visual_channels, descriptor_channels, config):
    """
    This is the specific descriptor aggregation logic
    """
    import numpy as np
    import kwarray
    import kwimage
    import warnings
    image_visual_stack = []
    image_descriptor_stack = []

    # Outer loop for each image in dataset
    for coco_image in coco_images:

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

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            part_image = kwarray.robust_normalize(part_image)
            part_image = kwimage.ensure_uint255(part_image)

            if config['method'] == 'average':
                frame_descriptor = np.nanmean(part_descriptor, axis=(0, 1))
            elif config['method'] == 'middle':
                h, w = part_descriptor.shape[0:2]
                frame_descriptor = part_descriptor[h // 2, w // 2]
                frame_descriptor = np.nan_to_num(frame_descriptor)
            else:
                raise KeyError(config['method'])

        image_visual_stack.append(part_image)
        image_descriptor_stack.append(frame_descriptor)

    if config['method'] == 'average':
        sequence_descriptor = np.nanmean(np.stack(image_descriptor_stack), axis=0)
    elif config['method'] == 'middle':
        sequence_descriptor = image_descriptor_stack[len(image_descriptor_stack) // 2]
    else:
        raise KeyError(config['method'])

    return image_visual_stack, sequence_descriptor


def pil_write_animated_gif(fpath, image_list):
    """
    Helper for visualizations

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
