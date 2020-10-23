class tweak_app_config:
    """A context manager to run code with a tweaked Flask app configuration

    :param app:         the app in question
    :param addl_config: additional configuration to apply temporarily
    """

    def __init__(self, app, addl_config):
        self.app = app
        self.addl_config = addl_config

    def __enter__(self):
        self.old_config_vals = {}
        self.del_from_config = []

        for k, v in self.addl_config.items():
            try:
                self.old_config_vals[k] = self.app.config[k]
            except KeyError:
                self.del_from_config.append(k)

            self.app.config[k] = v

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k in self.del_from_config:
            del self.app.config[k]

        for k, v in self.old_config_vals.items():
            self.app.config[k] = v
