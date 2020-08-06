# Set the version
try:
    import importlib.metadata

    __version__ = importlib.metadata.version("noggin-aaa")
except ImportError:
    try:
        import pkg_resources

        try:
            __version__ = pkg_resources.get_distribution("noggin-aaa").version
        except pkg_resources.DistributionNotFound:
            # The app is not installed, but the flask dev server can run it nonetheless.
            __version__ = None
    except ImportError:
        __version__ = None
