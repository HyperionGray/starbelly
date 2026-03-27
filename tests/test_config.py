import pytest

import starbelly.config


LOCAL_INI = '''[database]
host = starbelly-host
db = starbelly-db
user = starbelly-app
password = normalpass
super_user = starbelly-admin
super_password = superpass'''


SYSTEM_INI = '''[database]
host =
port = 28015
db =
user =
password =
super_user =
super_password =

[rate_limiter]
capacity = 10000'''


def test_get_config(tmp_path):
    # Hack: modify the module's private _root variable to point at our temp
    # directory.
    starbelly.config._root = tmp_path

    # Create temp configuration files.
    config_dir = tmp_path / 'conf'
    config_dir.mkdir()

    with (config_dir / 'local.ini').open('w') as f:
        f.write(LOCAL_INI)

    with (config_dir / 'system.ini').open('w') as f:
        f.write(SYSTEM_INI)

    # Read configuration.
    config = starbelly.config.get_config()
    import logging
    logging.debug('secrions %r', config.sections())
    db = config['database']
    rl = config['rate_limiter']

    assert db['host'] == 'starbelly-host'
    assert db['port'] == '28015'
    assert db['db'] == 'starbelly-db'
    assert rl['capacity'] == '10000'


def test_get_config_from_env_file(tmp_path, monkeypatch):
    starbelly.config._root = tmp_path
    config_dir = tmp_path / 'conf'
    config_dir.mkdir()

    with (config_dir / 'system.ini').open('w') as f:
        f.write(SYSTEM_INI)
    with (config_dir / 'local.ini').open('w') as f:
        f.write(LOCAL_INI)

    override_file = tmp_path / 'override.ini'
    override_file.write_text('[database]\nhost = override-host\n')
    monkeypatch.setenv('STARBELLY_CONFIG', str(override_file))

    config = starbelly.config.get_config()
    assert config['database']['host'] == 'override-host'


def test_get_config_with_extra_files(tmp_path):
    starbelly.config._root = tmp_path
    config_dir = tmp_path / 'conf'
    config_dir.mkdir()

    with (config_dir / 'system.ini').open('w') as f:
        f.write(SYSTEM_INI)
    with (config_dir / 'local.ini').open('w') as f:
        f.write(LOCAL_INI)

    override_file = tmp_path / 'override.ini'
    override_file.write_text('[database]\nhost = cli-host\n')

    config = starbelly.config.get_config(extra_files=[str(override_file)])
    assert config['database']['host'] == 'cli-host'
