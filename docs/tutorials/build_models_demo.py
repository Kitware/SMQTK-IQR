# Generates models for IQR applcation with prepopulated descriptors.
# Generates image data set, descriptor set, and nearest neighbors index.
# Implements the 'PrePopulatedDescriptorGenerator' class

# Standard libraries
import logging
import os.path as osp
import os
import json
import os
import numpy as np

# SMQTK specific packages
import ubelt as ub
import scriptconfig as scfg
from smqtk_iqr.utils import cli
from smqtk_dataprovider import DataSet
from smqtk_dataprovider.impls.data_element.file import DataFileElement
from smqtk_descriptors.descriptor_element_factory import DescriptorElementFactory
from smqtk_descriptors import DescriptorSet
from smqtk_indexing import NearestNeighborsIndex
from smqtk_core.configuration import (
    from_config_dict,
)


# ---------------------------------------------------------------
class MyConfig(scfg.DataConfig):
    """
    Define the configuration class using the scriptconfig package for CLI args
    """

    verbose = scfg.Value(
        False, isflag=True, short_alias=["v"], help="Output additional debug logging."
    )
    config = scfg.Value(
        None,
        required=True,
        short_alias=["c"],
        help=ub.paragraph(
            """
            Path to the JSON configuration files. The first file
            provided should be the configuration file for the
            ``IqrSearchDispatcher`` web-application and the second
            should be the configuration file for the ``IqrService`` web-
            application.
            """
        ),
        nargs=2,
    )
    metadata = scfg.Value(
        None,
        short_alias=["m"],
        help=ub.paragraph(
            """
            Path to the JSON descriptor metadata files. Contains pairs of
            image and descriptor file paths.
            """
        ),
    )
    tab = scfg.Value(
        None,
        required=True,
        short_alias=["t"],
        help=ub.paragraph(
            """
            The configuration "tab" of the ``IqrSearchDispatcher``
            configuration to use. This informs what dataset to add the
            input data files to.
            """
        ),
    )


# ---------------------------------------------------------------
def remove_cache_files(ui_config, iqr_config) -> None:
    """
    Remove any existing cache files in defined in config file paths
    """
    data_cache = ui_config["iqr_tabs"]["GEOWATCH_DEMO"]["data_set"][
        "smqtk_dataprovider.impls.data_set.memory.DataMemorySet"
    ]["cache_element"]["smqtk_dataprovider.impls.data_element.file.DataFileElement"][
        "filepath"
    ]
    # Deleting the file
    if os.path.exists(data_cache):
        os.remove(data_cache)
        print(f"\nFile {data_cache} deleted successfully")
    else:
        print(f"File {data_cache} does not exist - will be generated")

    # Remove any existing cache files in descriptor set config file path
    descriptor_cache = iqr_config["iqr_service"]["plugins"]["descriptor_set"][
        "smqtk_descriptors.impls.descriptor_set.memory.MemoryDescriptorSet"
    ]["cache_element"]["smqtk_dataprovider.impls.data_element.file.DataFileElement"][
        "filepath"
    ]

    # Deleting the file if it exists
    if descriptor_cache and os.path.exists(descriptor_cache):
        os.remove(descriptor_cache)
        print(f"File '{descriptor_cache}' deleted successfully")
    else:
        print(f"File '{descriptor_cache}' does not exist - will be generated")


# ---------------------------------------------------------------
def generate_sets(manifest_path, data_set, descriptor_set, descriptor_elem_factory):
    """
    Loads metadata from the JSON file and builds a data by adding each image.
    Fromt the data set, each image UUID is used to generate the associated
    desciptor and build the descriptor set.
    """
    # Load JSON data from the file
    with open(manifest_path, "r") as json_file:
        data = json.load(json_file)

    # Access the list of image-descriptor pairs
    image_descriptor_pairs = data["Image_Descriptor_Pairs"]

    # Iterate over each pair to build the data set and descriptor set
    for pair in image_descriptor_pairs:

        # Extract image path and descriptor path
        image_path = pair["image_path"]
        image_path = osp.expanduser(image_path)

        desc_path = pair["desc_path"]
        desc_path = osp.expanduser(desc_path)

        if osp.isfile(image_path) and osp.isfile(desc_path):
            data_fe = DataFileElement(image_path, readonly=True)
            data_set.add_data(data_fe)

            # Load the associated descriptor json vector
            with open(desc_path, "rb") as f:
                json_vec = json.load(f)
            vector = np.array(json_vec)

            # Generate descriptor element with image uuid and known vector
            descriptor = descriptor_elem_factory.new_descriptor(data_fe.uuid())
            descriptor.set_vector(vector)

            descriptor_set.add_descriptor(descriptor)

        else:
            print("\n Image or descriptor file paths not found")

    return data_set, descriptor_set


# ---------------------------------------------------------------
# A simple function to get the nth descriptor from the descriptor set
# Displays the UUID and vector of the descriptor
def get_nth_descriptor(descriptor_set, n):
    desc_iter = descriptor_set.descriptors()
    for i in range(n):
        desc = next(desc_iter)
    print(f"\nDescriptor {n} info, uuid: {desc.uuid()}, vector: {desc.vector()}")
    return desc


# ---------------------------------------------------------------
def main() -> None:
    # Instantiate the configuration class and gather the arguments
    args = MyConfig.cli(special_options=False)

    # --------------------------------------------------------------
    # Set up config values:
    ui_config_filepath, iqr_config_filepath = args.config
    llevel = logging.DEBUG if args.verbose else logging.INFO
    manifest_path = args.metadata
    tab = args.tab

    # Not using `cli.utility_main_helper`` due to deviating from single-
    # config-with-default usage.
    cli.initialize_logging(logging.getLogger("smqtk_iqr"), llevel)
    cli.initialize_logging(logging.getLogger("__main__"), llevel)
    log = logging.getLogger(__name__)

    log.info("Loading UI config: '{}'".format(ui_config_filepath))
    ui_config, ui_config_loaded = cli.load_config(ui_config_filepath)
    log.info("Loading IQR config: '{}'".format(iqr_config_filepath))
    iqr_config, iqr_config_loaded = cli.load_config(iqr_config_filepath)
    if not (ui_config_loaded and iqr_config_loaded):
        raise RuntimeError("One or both configuration files failed to load.")

    # Ensure the given "tab" exists in UI configuration.
    if tab is None:
        log.error("No configuration tab provided to drive model generation.")
        exit(1)
    if tab not in ui_config["iqr_tabs"]:
        log.error(
            "Invalid tab provided: '{}'. Available tags: {}".format(
                tab, list(ui_config["iqr_tabs"])
            )
        )
        exit(1)

    # ----------------------------------------------------------------
    # Gather Configurations
    log.info("Extracting plugin configurations")

    ui_tab_config = ui_config["iqr_tabs"][tab]
    iqr_plugins_config = iqr_config["iqr_service"]["plugins"]

    # Configure DataSet implementation and parameters
    data_set_config = ui_tab_config["data_set"]

    # Configure DescriptorElementFactory instance, which defines what
    # implementation of DescriptorElement to use for storing generated
    # descriptor vectors below.
    descriptor_elem_factory_config = iqr_plugins_config["descriptor_factory"]

    # Configure the DescriptorSet instance into which the descriptor elements
    # are added.
    descriptor_set_config = iqr_plugins_config["descriptor_set"]

    # Configure NearestNeighborIndex algorithm implementation, parameters and
    # persistent model component locations (if implementation has any).
    nn_index_config = iqr_plugins_config["neighbor_index"]

    # --------------------------------------------------------------
    # Remove any existing cache files in data set config file path
    remove_cache_files(ui_config, iqr_config)

    # ---------------------------------------------------------------
    # Initialize data/algorithms
    #
    # Constructing appropriate data structures and algorithms, needed for the
    # IQR demo application, in preparation for model training.
    log.info("Instantiating plugins")

    # Create instance of the class DataSet from the configuration
    data_set: DataSet = from_config_dict(data_set_config, DataSet.get_impls())
    descriptor_elem_factory = DescriptorElementFactory.from_config(
        descriptor_elem_factory_config
    )

    # Create instance of the class DescriptorSet from the configuration
    descriptor_set: DescriptorSet = from_config_dict(
        descriptor_set_config, DescriptorSet.get_impls()
    )

    # Create instance of the class NearestNeighborsIndex from the configuration
    nn_index: NearestNeighborsIndex = from_config_dict(
        nn_index_config, NearestNeighborsIndex.get_impls()
    )

    # Generate data set and descriptor set from the JSON manifest file
    data_set, descriptor_set = generate_sets(
        manifest_path, data_set, descriptor_set, descriptor_elem_factory
    )

    print(f"\nData set with {data_set.count()} elements created")
    print(f"Descriptor set with {descriptor_set.count()} elements created\n")

    log.info("Building nearest neighbors index {}".format(nn_index))
    nn_index.build_index(descriptor_set)

    # Debugging/Test - test nnindex with a descriptor
    desc_test = get_nth_descriptor(descriptor_set, 4)
    nn_test = nn_index.nn(desc_test, 3)
    print("\nNearest Neighbors: ", nn_test)


if __name__ == "__main__":
    main()
