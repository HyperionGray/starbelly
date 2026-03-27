import configparser
import os
import pathlib


_root = pathlib.Path(__file__).resolve().parent.parent


def get_path(relpath):
    ''' Get absolute path to a project-relative path. '''
    return _root / relpath


def get_config(extra_files=None):
    '''
    Read the application configuration from the standard configuration files.

    Additional configuration files can be loaded via the STARBELLY_CONFIG
    environment variable and/or by explicitly passing ``extra_files``.
    Later files override earlier files.

    :param iterable extra_files: Optional additional config file paths.
    :rtype: ConfigParser
    '''
    config_dir = get_path("conf")
    config_files = [
        config_dir / "system.ini",
        config_dir / "local.ini",
    ]
    env_config = os.getenv('STARBELLY_CONFIG')
    if env_config:
        config_files.append(pathlib.Path(env_config).expanduser())
    if extra_files:
        config_files.extend(pathlib.Path(path).expanduser() for path in extra_files)
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_files)
    return config
