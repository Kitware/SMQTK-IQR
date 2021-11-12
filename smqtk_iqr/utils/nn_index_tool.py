"""
TODO: Adapt this into SMQTK if/when generalized, click usage in SMQTK.
"""
import click
import logging
from typing import Dict

from smqtk_indexing import NearestNeighborsIndex
from smqtk_descriptors import DescriptorSet
from smqtk_iqr.utils.cli import initialize_logging, load_config, output_config
from smqtk_core.configuration import from_config_dict, make_default_config

LOG = logging.getLogger(__name__)


def build_default_config() -> Dict:
    return {
        'descriptor_set': make_default_config(DescriptorSet.get_impls()),
        'neighbor_index': make_default_config(NearestNeighborsIndex.get_impls()),
    }


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-v', '--verbose',
              default=0, count=True,
              help="This option must be provided before any command. "
                   "Provide once for additional informational logging. "
                   "Provide a second time for additional debug logging.")
def cli_group(verbose: int) -> None:
    """
    Tool for building a nearest neighbors index from an input descriptor set.

    The index is built, not updated. If the index configured must not be
    read-only and any persisted index, if already existing, may be overwritten.
    """
    llevel = logging.WARN - (10 * verbose)
    # Attempting just setting the root logger. If this becomes too verbose,
    # initially relevant namespaces manually.
    initialize_logging(logging.getLogger(), llevel)
    LOG.info("Displaying informational logging.")
    LOG.debug("Displaying debug logging.")


@click.command('config')
@click.argument('output_filepath')
@click.option('-c', '--input-config',
              type=click.Path(exists=True, dir_okay=False),
              default=None,
              help='Optional existing configuration file to update with '
                   'defaults.')
@click.option('-o', '--overwrite',
              default=False, is_flag=True,
              help='If the given filepath should be overwritten if it '
                   'already exists.')
def cli_config(output_filepath: str, input_config: str, overwrite: bool) -> None:
    """
    Generate a default or template JSON configuration file for this tool.
    """
    if input_config is not None:
        c_dict, success = load_config(input_config, build_default_config())
        if not success:
            raise RuntimeError(
                "Did not load input configuration file '{}' "
                "successfully.")
    else:
        c_dict = build_default_config()
    output_config(output_filepath, c_dict, overwrite=overwrite)


@click.command('build')
@click.argument('config_filepath',
                type=click.Path(exists=True, dir_okay=False))
def cli_build(config_filepath: str) -> None:
    """
    Build a new nearest-neighbors index from the configured descriptor set's
    contents.
    """
    config_dict, success = load_config(config_filepath,
                                       defaults=build_default_config())
    # Defaults are insufficient so we assert that the configuration file was
    # (successfully) loaded.
    if not success:
        raise RuntimeError("Failed to load configuration file.")

    descr_set = from_config_dict(config_dict['descriptor_set'],
                                 DescriptorSet.get_impls())

    nn_index = from_config_dict(config_dict['neighbor_index'],
                                NearestNeighborsIndex.get_impls())

    # TODO: reduced amount used for building ("training") and remainder used
    #       for update.
    nn_index.build_index(descr_set)


# Non-destructive update command?


cli_group.add_command(cli_config)
cli_group.add_command(cli_build)
