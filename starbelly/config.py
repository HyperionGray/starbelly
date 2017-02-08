import configparser
import os

from . import get_path


def get_config():
    """
    Read the application configuration from the standard configuration files.
    """

    config_dir = get_path("conf")

    config_files = [
        os.path.join(config_dir, "system.ini"),
        os.path.join(config_dir, "local.ini"),
    ]

    return merge_config_files(*config_files)


def merge_config_files(*paths):
    """
    Combine configuration files from one or more INI-style config files.
    The config files are merged together in order. Later configuration
    files can override earlier configuration files. Missing files are
    ignored.
    Use this mechanism for cascading configuration files. E.g.
    one config file is version controlled and the other config file is
    an optional, user-controlled file that can be used to customize a
    local deployment.
    """

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(paths)

    return config
