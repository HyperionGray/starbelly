import os

import starbelly.config


LOCAL_INI = '''[database]
host = starbelly-host
db = starbelly-db
user = starbelly-app
password = localpass
super_user = starbelly-admin
super_password = superpass'''


SYSTEM_INI = '''[database]
host = starbelly-system-host
port = 28015
db = starbelly-system-db
user = starbelly-system-user
password = systempass
super_user = starbelly-admin
super_password = systemsuperpass

[rate_limiter]
capacity = 10000'''


def _write_config_pair(config_dir, system_ini=SYSTEM_INI, local_ini=LOCAL_INI):
    config_dir.mkdir()
    with (config_dir / 'system.ini').open('w') as f:
        f.write(system_ini)
    with (config_dir / 'local.ini').open('w') as f:
        f.write(local_ini)


def test_get_config(tmp_path):
    # Hack: modify the module's private _root variable to point at our temp
    # directory.
    starbelly.config._root = tmp_path

    # Create temp configuration files.
    config_dir = tmp_path / 'conf'
    _write_config_pair(config_dir)

    # Read configuration.
    config = starbelly.config.get_config()
    db = config['database']
    rl = config['rate_limiter']

    assert db['host'] == 'starbelly-host'
    assert db['port'] == '28015'
    assert db['db'] == 'starbelly-db'
    assert rl['capacity'] == '10000'


def test_get_config_from_config_dir_argument(tmp_path):
    config_dir = tmp_path / 'custom-conf'
    _write_config_pair(config_dir)

    config = starbelly.config.get_config(config_dir=config_dir)
    db = config['database']
    assert db['host'] == 'starbelly-host'
    assert db['db'] == 'starbelly-db'


def test_get_config_from_env_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / 'env-conf'
    _write_config_pair(config_dir)
    monkeypatch.setenv('STARBELLY_CONFIG_DIR', str(config_dir))

    config = starbelly.config.get_config()
    db = config['database']
    assert db['host'] == 'starbelly-host'
    assert db['db'] == 'starbelly-db'


def test_get_config_from_env_config_files(tmp_path, monkeypatch):
    first = tmp_path / 'first.ini'
    second = tmp_path / 'second.ini'
    first.write_text('[database]\nhost=from-first\ndb=from-first\n')
    second.write_text('[database]\ndb=from-second\n', encoding='utf8')

    env_value = str(first) + os.pathsep + str(second)
    monkeypatch.setenv('STARBELLY_CONFIG_FILES', env_value)

    config = starbelly.config.get_config()
    db = config['database']
    assert db['host'] == 'from-first'
    assert db['db'] == 'from-second'


def test_get_config_explicit_files_override_env(tmp_path, monkeypatch):
    env_file = tmp_path / 'env.ini'
    arg_file = tmp_path / 'arg.ini'
    env_file.write_text('[database]\nhost=env-host\n', encoding='utf8')
    arg_file.write_text('[database]\nhost=arg-host\n', encoding='utf8')
    monkeypatch.setenv('STARBELLY_CONFIG_FILES', str(env_file))

    config = starbelly.config.get_config(config_files=[arg_file])
    assert config['database']['host'] == 'arg-host'
