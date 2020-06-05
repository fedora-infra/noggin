import python_freeipa
from flask import render_template, make_response


class IPAErrorHandler:
    def __init__(self, app, error_template):
        self.app = app
        self.template = error_template
        self.init_app()

    def init_app(self):
        self.app.wsgi_app = IPAWSGIMiddleware(
            self.app.wsgi_app, self.get_error_response
        )

    def get_error_response(self, error):
        self.app.logger.error(f"Uncaught IPA exception: {error}")
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
