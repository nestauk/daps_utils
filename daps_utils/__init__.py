import os

from .__initplus__ import __basedir__, load_config, load_current_version

__version__ = load_current_version()

if "IN_SETUP" not in os.environ:
    from .tasks import (
        MetaflowTask,
        CurateTask,
        ForceableTask,
        DapsTaskMixin,
        DapsRootTask,
    )
    from .flow import DapsFlowMixin

    config = load_config()
