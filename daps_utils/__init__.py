from .__initplus__ import path_to_init, __basedir__, load_config
try:
    from .breadcrumbs import drop_breadcrumb as talk_to_luigi
    from .tasks import _MetaflowTask, MetaflowTask
    config = load_config()
except ModuleNotFoundError:  # For integration with setup.py
    pass




def load_current_version():
    """Load the current version of this package."""
    path_to_version = path_to_init(__file__) / "VERSION"
    with open(path_to_version) as f:
        v = f.read()
    return v


__version__ = load_current_version()
