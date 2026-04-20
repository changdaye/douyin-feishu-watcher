import app


def test_package_version_exists() -> None:
    assert app.__version__ == "0.1.0"
