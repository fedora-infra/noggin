import python_freeipa
from flask import current_app, make_response, render_template


class IPAErrorHandler:
    def __init__(self, app=None, error_template="ipa_error.html"):
        self.template = error_template
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.register_error_handler(
            python_freeipa.exceptions.FreeIPAError, self.get_error_response
        )

    def get_error_response(self, error):
        current_app.logger.error(f"Uncaught IPA exception: {error}")
        return make_response(render_template(self.template, error=error), 500)
