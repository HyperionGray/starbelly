import configparser
import os
import pathlib


_root = pathlib.Path(__file__).resolve().parent.parent


def get_path(relpath):
    ''' Get absolute path to a project-relative path. '''
    return _root / relpath


def _coerce_paths(paths):
    ''' Convert any path-like values to pathlib.Path objects. '''
    return [pathlib.Path(path).expanduser() for path in paths]


def _default_config_files(config_dir):
    ''' Return the default system/local config file pair for a directory. '''
    return [
        pathlib.Path(config_dir) / 'system.ini',
        pathlib.Path(config_dir) / 'local.ini',
    ]


def get_config(config_files=None, config_dir=None):
    '''
    Read the application configuration from the standard configuration files.

    Config resolution order:
    1. explicit ``config_files`` argument (if provided)
    2. ``STARBELLY_CONFIG_FILES`` (os.pathsep-separated absolute/relative paths)
    3. ``config_dir`` argument (if provided) and its system/local defaults
    4. ``STARBELLY_CONFIG_DIR`` and its system/local defaults
    5. project ``conf/`` and its system/local defaults

    For all modes, files are read in order and later files override earlier
    values.

    :param list[str|pathlib.Path] config_files: (Optional) explicit config
        files to load in order.
    :param str|pathlib.Path config_dir: (Optional) directory containing
        ``system.ini`` and ``local.ini``.
    :rtype: ConfigParser
    '''
    if config_files is None:
        env_files = os.environ.get('STARBELLY_CONFIG_FILES')
        if env_files:
            config_files = _coerce_paths([
                path for path in env_files.split(os.pathsep) if path
            ])
        else:
            if config_dir is None:
                config_dir = os.environ.get('STARBELLY_CONFIG_DIR')
            if config_dir is None:
                config_dir = get_path('conf')
            config_files = _default_config_files(pathlib.Path(config_dir).expanduser())
    else:
        config_files = _coerce_paths(config_files)

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read([str(path) for path in config_files])
    return config
