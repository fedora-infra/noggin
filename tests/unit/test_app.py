import os

import pytest

from noggin.app import create_app


@pytest.fixture
def environ_config():
    varname = "NOGGIN_CONFIG_PATH"
    old_config_value = os.getenv(varname)
    os.environ[varname] = "defaults.py"
    yield
    if old_config_value is None:
        del os.environ[varname]
    else:
        os.environ[varname] = old_config_value


def test_env_var(mocker, app_config, environ_config):
    from_envvar = mocker.patch("flask.config.Config.from_envvar")
    create_app(app_config)
    from_envvar.assert_called_once_with("NOGGIN_CONFIG_PATH")


def test_templates_reload(app_config):
    config = app_config.copy()
    config["TEMPLATES_AUTO_RELOAD"] = True
    app = create_app(config)
    assert app.jinja_env.auto_reload is True


def test_logging(mocker, app_config):
    config = app_config.copy()
    config["LOGGING"] = "dummy-logging-config"
    logging_config = mocker.patch("noggin.app.dictConfig")
    create_app(config)
    logging_config.assert_called_once_with("dummy-logging-config")


def test_templates_custom_directory_insertion(app_config, tmp_path):
    tpl_dir = tmp_path / "templates"
    os.makedirs(tpl_dir)
    config = app_config.copy()
    config["TEMPLATES_CUSTOM_DIRECTORIES"] = [tpl_dir]
    app = create_app(config)
    # Use the template placeholder
    with open(tpl_dir / "after-navbar.html", "w") as tpl:
        tpl.write("TESTING TEMPLATES CUSTOM DIR\n")
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert "TESTING TEMPLATES CUSTOM DIR" in response.get_data(as_text=True)


def test_templates_custom_directory_override(app_config, tmp_path):
    tpl_dir = tmp_path / "templates"
    os.makedirs(tpl_dir)
    config = app_config.copy()
    config["TEMPLATES_CUSTOM_DIRECTORIES"] = [tpl_dir]
    app = create_app(config)
    # Override the whole page template
    with open(tpl_dir / "index.html", "w") as tpl:
        tpl.write("TESTING TEMPLATES CUSTOM DIR\n")
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert response.get_data(as_text=True) == "TESTING TEMPLATES CUSTOM DIR"
