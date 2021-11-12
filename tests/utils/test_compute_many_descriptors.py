import sys

from smqtk_iqr.utils.compute_many_descriptors import cli_parser, default_config
from smqtk_iqr.utils.cli import utility_main_helper


class TestComputeDescriptors (object):
    """
    Unit tests pertaining to the compute_many_descriptors utility script
    """

    def test_parse_args(self) -> None:
        """
        Test parsing command line args for the compute_many_descriptors application
        """
        sys.argv = ['compute_many_descriptors', '-v', '-b', '20', '--check-image', '-c',
                    'docker/smqtk_iqr_playground/default_confs/cpu/compute_many_descriptors.json',
                    '-f', 'list.txt', '-p', 'test.csv']

        args = cli_parser().parse_args()
        config = utility_main_helper(default_config(), args)

        assert args.file_list == 'list.txt'
        assert args.batch_size == 20
        assert args.check_image

        assert config['descriptor_generator'] is not None
        assert config['descriptor_set'] is not None
        assert config['descriptor_factory'] is not None
