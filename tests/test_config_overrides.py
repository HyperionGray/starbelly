import starbelly.config


LOCAL_INI = """[database]
host = local-host
db = local-db
user = local-user
password = local-password
super_user = local-admin
super_password = local-super-password
"""


SYSTEM_INI = """[database]
host =
port = 28015
db =
user =
password =
super_user =
super_password =
"""


EXTRA_INI = """[database]
host = extra-host
"""


ENV_INI = """[database]
host = env-host
"""


def _write_text(path, content):
    with path.open("w") as file:
        file.write(content)


def test_get_config_extra_files_override(tmp_path, monkeypatch):
    starbelly.config._root = tmp_path
    monkeypatch.delenv("STARBELLY_CONFIG", raising=False)

    config_dir = tmp_path / "conf"
    config_dir.mkdir()
    _write_text(config_dir / "local.ini", LOCAL_INI)
    _write_text(config_dir / "system.ini", SYSTEM_INI)

    extra_path = tmp_path / "extra.ini"
    _write_text(extra_path, EXTRA_INI)

    config = starbelly.config.get_config(extra_files=[extra_path])
    assert config["database"]["host"] == "extra-host"
    assert config["database"]["port"] == "28015"


def test_get_config_env_override(tmp_path, monkeypatch):
    starbelly.config._root = tmp_path

    config_dir = tmp_path / "conf"
    config_dir.mkdir()
    _write_text(config_dir / "local.ini", LOCAL_INI)
    _write_text(config_dir / "system.ini", SYSTEM_INI)

    env_path = tmp_path / "env.ini"
    _write_text(env_path, ENV_INI)
    monkeypatch.setenv("STARBELLY_CONFIG", str(env_path))

    config = starbelly.config.get_config()
    assert config["database"]["host"] == "env-host"
