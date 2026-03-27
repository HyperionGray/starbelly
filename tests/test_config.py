import os
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


def test_get_config(monkeypatch, tmp_path):
    # Hack: modify the module's private _root variable to point at our temp
    # directory.
    monkeypatch.setattr(starbelly.config, "_root", tmp_path)

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


def test_resolve_config_files_from_explicit_files(tmp_path):
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    first = config_dir / "first.ini"
    second = config_dir / "second.ini"
    first.write_text("[section]\nkey=one\n")
    second.write_text("[section]\nkey=two\n")

    result = starbelly.config.resolve_config_files(config_files=[first, second])
    assert result == [first, second]


def test_resolve_config_files_from_config_dir(tmp_path):
    config_dir = tmp_path / "custom_conf"
    config_dir.mkdir()

    result = starbelly.config.resolve_config_files(config_dir=config_dir)
    assert result == [
        config_dir / "system.ini",
        config_dir / "local.ini",
    ]


def test_get_config_uses_env_config_files(monkeypatch, tmp_path):
    first = tmp_path / "first.ini"
    second = tmp_path / "second.ini"
    first.write_text("[database]\nhost=from-first\n")
    second.write_text("[database]\nhost=from-second\n")

    monkeypatch.setenv(
        starbelly.config.ENV_CONFIG_FILES,
        f"{first}{os.pathsep}{second}",
    )
    config = starbelly.config.get_config()
    assert config["database"]["host"] == "from-second"


def test_get_config_uses_env_config_dir(monkeypatch, tmp_path):
    config_dir = tmp_path / "env_conf"
    config_dir.mkdir()
    (config_dir / "system.ini").write_text(
        "[database]\nhost=\nport=28015\ndb=\nuser=\npassword=\nsuper_user=\n"
        "super_password=\n"
    )
    (config_dir / "local.ini").write_text("[database]\nhost=env-host\n")

    monkeypatch.setenv(starbelly.config.ENV_CONFIG_DIR, str(config_dir))
    config = starbelly.config.get_config()
    assert config["database"]["host"] == "env-host"
