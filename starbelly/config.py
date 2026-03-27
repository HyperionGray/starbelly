import configparser
import os
import pathlib


_root = pathlib.Path(__file__).resolve().parent.parent


def get_path(relpath):
    ''' Get absolute path to a project-relative path. '''
    return _root / relpath


def get_config_files(extra_files=None):
    '''
    Get the ordered list of configuration files to load.

    Config files are loaded in this order:
    1. conf/system.ini
    2. conf/local.ini
    3. files from STARBELLY_CONFIG (os.pathsep-separated)
    4. files from the ``extra_files`` argument
    '''
    config_dir = get_path("conf")
    config_files = [
        config_dir / "system.ini",
        config_dir / "local.ini",
    ]
    env_files = os.getenv("STARBELLY_CONFIG", "").split(os.pathsep)
    config_files.extend(pathlib.Path(path) for path in env_files if path)
    if extra_files is not None:
        config_files.extend(pathlib.Path(path) for path in extra_files if path)
    return config_files


def get_config(extra_files=None):
    '''
    Read the application configuration from the standard configuration files.

    :rtype: ConfigParser
    '''
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(get_config_files(extra_files))
    return config
