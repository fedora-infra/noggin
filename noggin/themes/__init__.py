from flask import Blueprint


class Theme:
    def __init__(self, app=None, whitenoise=None):
        if app is not None:
            self.init_app(app, whitenoise)

    def init_app(self, app, whitenoise=None):
        name = app.config.get('THEME')
        blueprint = Blueprint(
            'theme',
            __name__,
            static_url_path='/theme/static',
            static_folder=f"{name}/static/",
            template_folder=f"{name}/templates/",
        )
        app.register_blueprint(blueprint)

        # Use Whitenoise to serve the static files
        if whitenoise:
            whitenoise.add_files(
                f"{app.root_path}/themes/{name}/static/", prefix="/theme/static"
            )
