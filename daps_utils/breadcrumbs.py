"""
breadcrumbs
-----------

A way of communicating the output of metaflow tasks
with the rest of the world. Metaflow will drop it's output
in an S3 path, but when Metaflow is run in Docker, the
memory of it's S3 path is lost. To remedy this, we
monkey patch the Flow "start" step with a decorator
so that it prints out the S3 path via a tell-tale breadcrumb.
The breadcrumb can then be picked up from the Docker logs
via a regex. Hacky, but effective!
"""

from metaflow import step, S3
import re

BREADCRUMB = "===>>> {} <<<==="


class BreadCrumbError(Exception):
    pass


def _drop_breadcrumb(func):
    def wrapper(self, *args, **kwargs):
        with S3(run=self) as s3:
            print(BREADCRUMB.format(s3._s3root))
        func(self, *args, **kwargs)
    return wrapper


def drop_breadcrumb(flow):
    """Decorator on a Flow to force the "start" step
    to drop the breadcrumb."""
    flow.start = step(_drop_breadcrumb(flow.start))
    return flow


def pickup_breadcrumb(logs):
    """Pick up the breadcrumb via a regex of the logs"""
    pattern = BREADCRUMB.format('(.*)')
    results = re.findall(pattern, logs)
    if len(results) == 0:
        raise BreadCrumbError("Could not find the Flow's S3 root URL. "
                              "Did you forget to decorate your Flow with "
                              "'@drop_breadcrumb'?")
    elif len(results) > 1:
        raise BreadCrumbError("Found multiple instances of the pattent "
                              f"'{BREADCRUMB}'. Do not include this pattern "
                              "in your output: it is reserved for "
                              "breadcrumbs.")
    return results[0]
