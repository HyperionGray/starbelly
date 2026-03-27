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


def test_get_config(tmp_path, monkeypatch):
    # Point config root to our temp directory.
    monkeypatch.setattr(starbelly.config, '_root', tmp_path)

    # Create temp configuration files.
    config_dir = tmp_path / 'conf'
    config_dir.mkdir()

    with (config_dir / 'local.ini').open('w') as f:
        f.write(LOCAL_INI)

    with (config_dir / 'system.ini').open('w') as f:
        f.write(SYSTEM_INI)

    # Read configuration.
    config = starbelly.config.get_config()
    db = config['database']
    rl = config['rate_limiter']

    assert db['host'] == 'starbelly-host'
    assert db['port'] == '28015'
    assert db['db'] == 'starbelly-db'
    assert rl['capacity'] == '10000'


def test_get_config_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setattr(starbelly.config, '_root', tmp_path)

    config_dir = tmp_path / 'conf'
    config_dir.mkdir()
    with (config_dir / 'local.ini').open('w') as f:
        f.write(LOCAL_INI)
    with (config_dir / 'system.ini').open('w') as f:
        f.write(SYSTEM_INI)

    env = {
        'STARBELLY_DB_HOST': 'env-db-host',
        'STARBELLY_DB_PORT': '39000',
        'STARBELLY_DB_NAME': 'env-db-name',
        'STARBELLY_DB_USER': 'env-db-user',
        'STARBELLY_DB_PASSWORD': 'env-db-password',
        'STARBELLY_DB_SUPER_USER': 'env-super-user',
        'STARBELLY_DB_SUPER_PASSWORD': 'env-super-password',
        'STARBELLY_RATE_LIMITER_CAPACITY': '12345',
    }
    config = starbelly.config.get_config(env=env)
    db = config['database']
    rl = config['rate_limiter']

    assert db['host'] == 'env-db-host'
    assert db['port'] == '39000'
    assert db['db'] == 'env-db-name'
    assert db['user'] == 'env-db-user'
    assert db['password'] == 'env-db-password'
    assert db['super_user'] == 'env-super-user'
    assert db['super_password'] == 'env-super-password'
    assert rl['capacity'] == '12345'


def test_get_config_custom_config_files(tmp_path, monkeypatch):
    monkeypatch.setattr(starbelly.config, '_root', tmp_path)

    custom_system = tmp_path / 'first.ini'
    custom_local = tmp_path / 'second.ini'

    with custom_system.open('w') as f:
        f.write('[database]\nhost = first-host\nport = 28015\ndb = first-db\n')
    with custom_local.open('w') as f:
        f.write('[database]\nhost = second-host\n')

    env = {
        'STARBELLY_CONFIG_FILES':
            f'{custom_system}{starbelly.config.os.pathsep}{custom_local}',
    }
    config = starbelly.config.get_config(env=env)
    db = config['database']

    assert db['host'] == 'second-host'
    assert db['db'] == 'first-db'


def test_get_config_custom_config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(starbelly.config, '_root', tmp_path)

    custom_dir = tmp_path / 'config-root'
    custom_dir.mkdir()
    with (custom_dir / 'system.ini').open('w') as f:
        f.write('[database]\nport = 28016\ndb = system-db\n')
    with (custom_dir / 'local.ini').open('w') as f:
        f.write('[database]\nhost = local-host\n')

    env = {'STARBELLY_CONFIG_DIR': str(custom_dir)}
    config = starbelly.config.get_config(env=env)
    db = config['database']

    assert db['host'] == 'local-host'
    assert db['port'] == '28016'
    assert db['db'] == 'system-db'
