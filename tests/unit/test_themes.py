from noggin.themes import Theme


def test_flask_ext_without_whitenoise(mocker):
    app = mocker.Mock()
    Theme(app)
    app.register_blueprint.assert_called_once()


def test_flask_ext_with_whitenoise(mocker):
    app = mocker.Mock()
    app.root_path = "/somewhere"
    app.config = {"THEME": "dummy-theme"}
    whitenoise = mocker.Mock()
    Theme(app, whitenoise)
    app.register_blueprint.assert_called_once()
    whitenoise.add_files.assert_called_once_with(
        "/somewhere/themes/dummy-theme/static/", prefix="/theme/static"
    )
