import configparser
import os
import pathlib


_root = pathlib.Path(__file__).resolve().parent.parent
_config_files_env_var = "STARBELLY_CONFIG_FILES"
_config_dir_env_var = "STARBELLY_CONFIG_DIR"
_env_overrides = {
    "database": {
        "host": "STARBELLY_DB_HOST",
        "port": "STARBELLY_DB_PORT",
        "db": "STARBELLY_DB_NAME",
        "user": "STARBELLY_DB_USER",
        "password": "STARBELLY_DB_PASSWORD",
        "super_user": "STARBELLY_DB_SUPER_USER",
        "super_password": "STARBELLY_DB_SUPER_PASSWORD",
    },
    "rate_limiter": {
        "capacity": "STARBELLY_RATE_LIMITER_CAPACITY",
    },
}


def get_path(relpath):
    ''' Get absolute path to a project-relative path. '''
    return _root / relpath


def _get_config_files(config_dir, env):
    config_files_value = env.get(_config_files_env_var)
    if config_files_value:
        config_files = []
        for path in config_files_value.split(os.pathsep):
            path = path.strip()
            if path:
                config_files.append(pathlib.Path(path).expanduser())
        if config_files:
            return config_files
    return [
        config_dir / "system.ini",
        config_dir / "local.ini",
    ]


def _apply_env_overrides(config, env):
    for section_name, options in _env_overrides.items():
        if section_name not in config:
            config.add_section(section_name)
        section = config[section_name]
        for option_name, env_var in options.items():
            if env_var in env:
                section[option_name] = env[env_var]


def get_config(env=None):
    '''
    Read the application configuration from the standard configuration files.

    :rtype: ConfigParser
    '''
    env = env if env is not None else os.environ
    config_dir = pathlib.Path(
        env.get(_config_dir_env_var, get_path("conf"))
    ).expanduser()
    config_files = _get_config_files(config_dir, env)
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_files)
    _apply_env_overrides(config, env)
    return config
