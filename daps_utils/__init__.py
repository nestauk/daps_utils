from .__initplus__ import __basedir__, load_config, load_current_version

try:
    from .breadcrumbs import drop_breadcrumb as talk_to_luigi
    from .tasks import MetaflowTask, CurateTask, ForceableTask
    from .flow import DapsFlowMixin
    config = load_config()
except ModuleNotFoundError as exc:  # For integration with setup.py
    print(exc)
    pass

__version__ = load_current_version()
