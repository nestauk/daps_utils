from .__initplus__ import load_current_version, __basedir__, load_config
try:
    from .breadcrumbs import drop_breadcrumb as talk_to_luigi
    from .tasks import _MetaflowTask, MetaflowTask
    config = load_config()
except ModuleNotFoundError:  # For integration with setup.py
    pass
    

__version__ = load_current_version()
