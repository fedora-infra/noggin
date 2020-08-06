from werkzeug.utils import find_modules, import_string


def import_all(import_name):
    for module in find_modules(import_name, include_packages=True, recursive=True):
        import_string(module)
