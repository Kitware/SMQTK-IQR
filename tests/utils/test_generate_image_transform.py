import sys

from smqtk_iqr.utils.generate_image_transform import cli_parser, default_config
from smqtk_iqr.utils.cli import utility_main_helper


class TestGenerateImageTransformTool (object):
    """
    Unit tests pertaining to the generate_image_transform utility script
    """

    def test_parse_args(self) -> None:
        """
        Test parsing command line args for the generate_image_transform index application
        """
        sys.argv = ['generate_image_transform', '-c',
                    'docker/smqtk_iqr_playground/default_confs/generate_image_transform.tiles.json']

        args = cli_parser().parse_args()
        config = utility_main_helper(default_config(), args, default_config_valid=False)

        assert config['crop']['tile_shape'] is not None
        assert config['crop']['tile_stride'] is not None
