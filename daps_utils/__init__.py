from .__initplus__ import load_current_version, __basedir__, load_config
try:
    from .breadcrumbs import drop_breadcrumb as talk_to_luigi
    from .tasks import MetaflowTask, CurateTask
    config = load_config()
except ModuleNotFoundError as exc:  # For integration with setup.py
    print(exc)
    pass

__version__ = load_current_version()
