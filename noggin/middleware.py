import python_freeipa
from flask import current_app, make_response, render_template


class IPAErrorHandler:
    def __init__(self, app=None, error_template="ipa_error.html"):
        self.template = error_template
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.wsgi_app = IPAWSGIMiddleware(app.wsgi_app, self.get_error_response)

    def get_error_response(self, error):
        current_app.logger.error(f"Uncaught IPA exception: {error}")
        return make_response(render_template(self.template, error=error), 500)


class IPAWSGIMiddleware:
    def __init__(self, wsgi_app, error_factory):
        self.wsgi_app = wsgi_app
        self.error_factory = error_factory

    def __call__(self, environ, start_response):
        try:
            return self.wsgi_app(environ, start_response)
        except python_freeipa.exceptions.FreeIPAError as e:
            return self.error_factory(e)(environ, start_response)
