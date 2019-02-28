import configparser
import pathlib


_root = pathlib.Path(__file__).resolve().parent.parent


def get_path(relpath):
    ''' Get absolute path to a project-relative path. '''
    return _root / relpath


def get_config():
    '''
    Read the application configuration from the standard configuration files.

    :rtype: ConfigParser
    '''
    config_dir = get_path("conf")
    config_files = [
        config_dir / "system.ini",
        config_dir / "local.ini",
    ]
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_files)
    return config
