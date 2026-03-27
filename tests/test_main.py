import pytest

from starbelly import __main__
from starbelly.version import __version__


def test_get_args_version_flag(monkeypatch):
    monkeypatch.setattr(__main__.sys, 'argv', ['starbelly', '--version'])
    args = __main__.get_args()
    assert args.version is True


def test_main_prints_version_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(__main__.sys, 'argv', ['starbelly', '--version'])
    called = {'configure': 0, 'bootstrap': 0}

    def fake_configure_logging(*_args, **_kwargs):
        called['configure'] += 1

    class FakeBootstrap:
        def __init__(self, *_args, **_kwargs):
            called['bootstrap'] += 1

        def run(self):
            called['bootstrap'] += 1

    monkeypatch.setattr(__main__, 'configure_logging', fake_configure_logging)
    monkeypatch.setattr(__main__, 'Bootstrap', FakeBootstrap)

    exit_code = __main__.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == f'starbelly {__version__}'
    assert called['configure'] == 0
    assert called['bootstrap'] == 0


def test_main_configures_logging_and_runs_bootstrap(monkeypatch):
    monkeypatch.setattr(
        __main__.sys,
        'argv',
        ['starbelly', '--log-level', 'info', '--ip', '0.0.0.0', '--port', '9000'],
    )
    called = {'configure': 0, 'bootstrap': 0, 'run': 0}

    def fake_configure_logging(log_level, error_log):
        called['configure'] += 1
        assert log_level == 'info'
        assert error_log is None

    def fake_get_config():
        return {'loaded': True}

    class FakeBootstrap:
        def __init__(self, config, args):
            called['bootstrap'] += 1
            assert config == {'loaded': True}
            assert args.ip == '0.0.0.0'
            assert args.port == 9000

        def run(self):
            called['run'] += 1

    monkeypatch.setattr(__main__, 'configure_logging', fake_configure_logging)
    monkeypatch.setattr(__main__, 'get_config', fake_get_config)
    monkeypatch.setattr(__main__, 'Bootstrap', FakeBootstrap)

    exit_code = __main__.main()
    assert exit_code == 0
    assert called == {'configure': 1, 'bootstrap': 1, 'run': 1}
