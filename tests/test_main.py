import pytest

from starbelly import __main__ as main_mod
from starbelly.version import __version__


def test_get_args_defaults():
    args = main_mod.get_args([])
    assert args.log_level == "warning"
    assert args.ip == "127.0.0.1"
    assert args.port == 8000
    assert not args.reload
    assert args.error_log is None


def test_get_args_version_flag():
    args = main_mod.get_args(["--version"])
    assert args.version


def test_get_version_output():
    assert main_mod.get_version_output() == f"Starbelly {__version__}"
