"""
Helper functions for command line utilities.
"""
import argparse
import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from typing import Tuple, Dict, Optional, Callable, Iterable, Any

from smqtk_core.dict import merge_dict


LOG = logging.getLogger(__name__)


def initialize_logging(
    logger: logging.Logger, stream_level: int = logging.WARNING,
    output_filepath: str = None, file_level: Optional[int] = None
) -> None:
    """
    Standard logging initialization.
    :param logger: Logger instance to initialize
    :param stream_level: Logging level to set for the stderr stream formatter.
    :param output_filepath: Output logging from the given logger to the provided
        file path. Currently, we log to that file indefinitely, i.e. no
        rollover. Rollover may be added in the future if the need arises.
    :param file_level: Logging level to output to the file. This the same as the
        stream level by default.
    """
    log_formatter = logging.Formatter(
        "%(levelname)7s - %(asctime)s - %(name)s.%(funcName)s - %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(stream_level)
    logger.addHandler(stream_handler)

    if output_filepath:
        # TODO: Setup rotating part of the handler?
        file_handler = logging.handlers.RotatingFileHandler(
            output_filepath, mode='w', delay=True
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(file_level or stream_level)
        logger.addHandler(file_handler)

    # Because there are two levels checked before a logging message is emitted:
    #   * the logging object's level
    #   * The stream handlers level
    logger.setLevel(min(stream_level, file_level or stream_level))


def load_config(
    config_path: str, defaults: Optional[Dict] = None
) -> Tuple[Dict, bool]:
    """
    Load the JSON configuration dictionary from the specified filepath.

    If the given path does not point to a valid file, we return an empty
    dictionary or the default dictionary if one was provided, returning False
    as our second return argument.

    :param config_path: Path to the (valid) JSON configuration file.

    :param defaults: Optional default configuration dictionary to merge loaded
        configuration into. If provided, it will be modified in place.

    :return: The result configuration dictionary and if we successfully loaded
        a JSON dictionary from the given filepath.

    """
    if defaults is None:
        defaults = {}
    loaded = False
    if config_path and os.path.isfile(config_path):
        with open(config_path) as cf:
            merge_dict(defaults, json.load(cf))
            loaded = True
    return defaults, loaded


def output_config(
    output_path: str, config_dict: Dict, overwrite: bool = False,
    error_rc: int = 1, log: Optional[logging.Logger] = None
) -> None:
    """
    If a valid output configuration path is provided, we output the given
    configuration dictionary as JSON or error if the file already exists (when
    overwrite is False) or cannot be written. We exit the program as long as
    ``output_path`` was given a value, with a return code of 0 if the file was
    written successfully, or the supplied return code (default of 1) if the
    write failed.

    Specified error return code cannot be 0, which is reserved for successful
    operation.

    :raises ValueError: If the given error return code is 0.

    :param output_path: Path to write the configuration file to.

    :param config_dict: Configuration dictionary containing JSON-compliant
        values.

    :param overwrite: If we should clobber any existing file at the specified
        path. We exit with the error code if this is false and a file exists at
        ``output_path``.

    :param error_rc: Custom integer error return code to use instead of 1.

    :param log: Optionally logging instance. Otherwise we use a local one.
    """
    error_rc = int(error_rc)
    if error_rc == 0:
        raise ValueError("Error return code cannot be 0.")
    if log is None:
        log = logging.getLogger(__name__)
    if output_path:
        if os.path.exists(output_path) and not overwrite:
            log.error("Output configuration file path already exists! (%s)",
                      output_path)
            sys.exit(error_rc)
        else:
            log.info("Outputting JSON configuration to: %s", output_path)
            with open(output_path, 'w') as f:
                json.dump(config_dict, f, indent=4, check_circular=True,
                          separators=(',', ': '), sort_keys=True)
            sys.exit(0)


class ProgressReporter:
    """
    Helper utility for reporting the state of a loop and the rate at which
    looping is occurring based on lapsed wall-time and a given reporting
    interval.

    Includes optional methods that are thread-safe.

    TODO: Add parameter for an optionally known total number of increments.
    """

    def __init__(
        self, log_func: Callable, interval: float, what_per_second: str = "Loops"
    ):
        """
        Initialize this reporter.

        :param log_func: Logging function to use.

        :param interval: Time interval to perform reporting in seconds.  If no
            reporting during incrementation should occur, infinity should be
            passed.

        :param str what_per_second:
            String label about what is happening or being iterated over per
            second. The provided string should make sense when followed by
            " per second ...".

        """
        self.log_func = log_func
        self.interval = float(interval)
        self.what_per_second = what_per_second

        self.lock = threading.RLock()
        # c_last : Increment count at the time of the last report. Updated after
        #          report in ``increment_report``.
        # c      : Current Increment count, updated in ``increment_report``.
        # c_delta: Delta between the increment current and previous count at the
        #          time of the last report. Updated at the time of reporting in
        #          ``increment_report``.
        self.c_last = self.c = self.c_delta = 0
        # t_last : Time of the last report. Updated after report in
        #          ``increment_report``.
        # t      : Current time, Updated in ``increment_report``
        # t_delta: Delta between current time and the time of the last report.
        #          Updated in ``increment_report``.
        self.t_last = self.t = self.t_delta = self.t_start = 0.0

        self.started = False

    def start(self) -> "ProgressReporter":
        """ Start the timing state of this reporter.

        Repeated calls to this method resets the state of the reporting for
        multiple uses.

        This method is thread-safe.

        :returns: Self

        """
        with self.lock:
            self.started = True
            self.c_last = self.c = self.c_delta = 0
            self.t_last = self.t = self.t_start = time.time()
            self.t_delta = 0.0
        return self

    def increment_report(self) -> None:
        """
        Increment counter and time since last report, reporting if delta exceeds
        the set reporting interval period.
        """
        if not self.started:
            raise RuntimeError("Reporter needs to be started first.")
        self.c += 1
        self.c_delta = self.c - self.c_last
        self.t = time.time()
        self.t_delta = self.t - self.t_last
        # Only report if its been ``interval`` seconds since the last
        # report.
        if self.t_delta >= self.interval:
            self.report()
            self.t_last = self.t
            self.c_last = self.c

    def increment_report_threadsafe(self) -> None:
        """
        The same as ``increment_report`` but additionally acquires a lock on
        resources first for thread-safety.

        This version of the method is a little more costly due to the lock
        acquisition.
        """
        with self.lock:
            self.increment_report()

    def report(self) -> None:
        """
        Report the current state.

        Does nothing if no increments have occurred yet.
        """
        if not self.started:
            raise RuntimeError("Reporter needs to be started first.")
        # divide-by-zero safeguard
        if self.t_delta > 0 and (self.t - self.t_start) > 0:
            self.log_func("%s per second %f (avg %f) "
                          "(%d current interval / %d total)"
                          % (self.what_per_second,
                             self.c_delta / self.t_delta,
                             self.c / (self.t - self.t_start),
                             self.c_delta,
                             self.c))

    def report_threadsafe(self) -> None:
        """
        The same as ``report`` but additionally acquires a lock on
        resources first for thread-safety.

        This version of the method is a little more costly due to the lock
        acquisition.
        """
        with self.lock:
            self.report()


def basic_cli_parser(
    description: str = None, configuration_group: bool = True
) -> argparse.ArgumentParser:
    """
    Generate an ``argparse.ArgumentParser`` with the given description and the
    basic options for verbosity and configuration/generation paths.

    The returned parser instance has an option for extra verbosity
    (-v/--verbose) and a group for configuration specification (-c/--config and
    configuration generation (-g/--generate-config) if enabled (true by
    default).

    :param description: Optional description string for the parser.

    :param configuration_group: Whether or not to include the configuration
        group options.

    :return: Argument parser instance with basic options.

    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('-v', '--verbose',
                        default=False, action='store_true',
                        help='Output additional debug logging.')

    if configuration_group:
        g_config = parser.add_argument_group('Configuration')
        g_config.add_argument('-c', '--config',
                              metavar="PATH",
                              help='Path to the JSON configuration file.')
        g_config.add_argument('-g', '--generate-config',
                              metavar="PATH",
                              help='Optionally generate a default '
                                   'configuration file at the specified path. '
                                   'If a configuration file was provided, we '
                                   'update the default configuration with the '
                                   'contents of the given configuration.')

    return parser


def utility_main_helper(
    default_config: Dict[str, Any], args: argparse.Namespace,
    additional_logging_domains: Iterable[str] = (),
    skip_logging_init: bool = False, default_config_valid: bool = False
) -> Dict:
    """
    Helper function for utilities standardizing logging initialization, CLI
    parsing and configuration loading/generation.

    Specific utilities should use this in their main function. This
    encapsulates the following standard actions:

        - using ``argparse`` parser results to drive logging initialization
          (can be skipped if initialized externally)
        - handling loaded configuration merger onto the default
        - handling configuration generation based on given default and possibly
          specified input config.

    :param default_config: Function returning default configuration (JSON)
        dictionary for the utility. This should take no arguments.

    :param args: Parsed arguments from argparse.ArgumentParser instance as
        returned from ``parser.parse_args()``.

    :param additional_logging_domains: We initialize logging on the base
        ``smqtk`` and ``__main__`` namespace. Any additional namespaces under
        which logging should be reported should be added here as an iterable.

    :param skip_logging_init: Skip initialize logging in this function because
        it is done elsewhere externally.

    :param default_config_valid: Whether the default config returned from the
        generator is a valid config to continue execution with or not.

    :return: Loaded configuration dictionary.

    """
    # noinspection PyUnresolvedReferences
    config_filepath = args.config
    # noinspection PyUnresolvedReferences
    config_generate = args.generate_config
    # noinspection PyUnresolvedReferences
    verbose = args.verbose

    if not skip_logging_init:
        llevel = logging.INFO
        if verbose:
            llevel = logging.DEBUG

        initialize_logging(logging.getLogger('smqtk_iqr'), llevel)
        initialize_logging(logging.getLogger('__main__'), llevel)
        for d in additional_logging_domains:
            initialize_logging(logging.getLogger(d), llevel)

    config, config_loaded = load_config(config_filepath, default_config)
    output_config(config_generate, config, overwrite=True)

    if not (config_loaded or default_config_valid):
        raise RuntimeError("No configuration loaded (not trusting default).")

    return config
