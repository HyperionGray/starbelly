import configparser
import os
import pathlib


_root = pathlib.Path(__file__).resolve().parent.parent
ENV_CONFIG_DIR = "STARBELLY_CONFIG_DIR"
ENV_CONFIG_FILES = "STARBELLY_CONFIG_FILES"
DEFAULT_CONFIG_FILENAMES = ("system.ini", "local.ini")


def get_path(relpath):
    ''' Get absolute path to a project-relative path. '''
    return _root / relpath


def resolve_config_files(config_files=None, config_dir=None):
    """
    Resolve which config files should be loaded.

    Precedence:
    1. Explicit ``config_files`` argument (highest priority)
    2. ``STARBELLY_CONFIG_FILES`` environment variable (os.pathsep-delimited)
    3. ``config_dir`` argument
    4. ``STARBELLY_CONFIG_DIR`` environment variable
    5. Project default ``conf/system.ini`` and ``conf/local.ini``
    """
    if config_files:
        return [pathlib.Path(path).expanduser() for path in config_files]

    env_files = os.getenv(ENV_CONFIG_FILES, "")
    if env_files.strip():
        return [
            pathlib.Path(path).expanduser()
            for path in env_files.split(os.pathsep)
            if path.strip()
        ]

    if config_dir is None:
        env_dir = os.getenv(ENV_CONFIG_DIR)
        if env_dir:
            config_dir = pathlib.Path(env_dir).expanduser()

    if config_dir is None:
        config_dir = get_path("conf")
    else:
        config_dir = pathlib.Path(config_dir).expanduser()

    return [config_dir / filename for filename in DEFAULT_CONFIG_FILENAMES]


def get_config(config_files=None, config_dir=None):
    '''
    Read the application configuration from the standard configuration files.

    :rtype: ConfigParser
    '''
    config_files = resolve_config_files(
        config_files=config_files,
        config_dir=config_dir,
    )
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read([str(path) for path in config_files])
    return config
