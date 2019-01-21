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
