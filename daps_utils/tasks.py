"""
tasks
-----

Common DAPS task types.
"""

import abc
import luigi
from luigi.contrib.s3 import S3Target, S3PathTask
from datetime import datetime as dt
from importlib import import_module
import inspect

from .docker_utils import get_metaflow_config
from .docker_utils import build_and_run_image
from .breadcrumbs import pickup_breadcrumb

from .parse_caller import get_main_caller_pkg
CALLER_PKG = get_main_caller_pkg(inspect.currentframe())


def import_pkg(daps_pkg):
    pkg = import_module(daps_pkg)
    for attr in ('config', '__basedir__', '__version__'):
        assert_hasattr(pkg, attr, daps_pkg)
    return pkg


def assert_hasattr(pkg, attr, pkg_name):
    if not hasattr(pkg, attr):
        raise AttributeError(f"{pkg_name} is expected to have attribute '{attr}'. "
                             "Have you run 'metaflowtask-init' from your package root?")


class MetaflowTask(luigi.Task):
    """Run metaflow Flows in Docker"""
    flow_path = luigi.Parameter()
    flow_tag = luigi.ChoiceParameter(choices=["dev", "production"],
                                     var_type=str, default="dev")
    rebuild_base = luigi.BoolParameter(default=False)
    rebuild_flow = luigi.BoolParameter(default=True)
    flow_kwargs = luigi.DictParameter(default={})
    preflow_kwargs = luigi.DictParameter(default={})
    container_kwargs = luigi.DictParameter(default={})
    requires_task = luigi.TaskParameter(default=S3PathTask)
    requires_task_kwargs = luigi.DictParameter(default={})

    @property
    def s3path(self):
        metaflow_config = get_metaflow_config()
        return metaflow_config['METAFLOW_DATASTORE_SYSROOT_S3']

    def requires(self):
        if self.requires_task is S3PathTask:
            return S3PathTask(self.s3path)
        return self.requires_task(**self.requires_task_kwargs)

    def run(self):
        if 'tag' in self.flow_kwargs:
            raise KeyError('"tag" argument should not be specified in "flow_kwargs". '
                           'Use "flow_tag" to specify this value')
        logs, tag = build_and_run_image(flow_path=self.flow_path,
                                        rebuild_base=self.rebuild_base,
                                        rebuild_flow=self.rebuild_flow,
                                        pkg=CALLER_PKG,
                                        flow_kwargs={'tag': self.flow_tag,
                                                     **self.flow_kwargs},
                                        preflow_kwargs=self.preflow_kwargs,
                                        **self.container_kwargs)
        breadcrumb = pickup_breadcrumb(logs)
        out = self.output().open('w')
        out.write(breadcrumb)
        out.close()

    def output(self):
        return S3Target(f'{self.s3path}/{self.task_id}')


class CurateTask(luigi.Task):
    """Run metaflow Flows in Docker, then curate the data
    and store the result in a database table.

    Args:
        model (SqlAlchemy model): A SqlAlchemy ORM, indicating the table
                                  of interest.
        flow_path (str): Path to your flow, relative to the flows directory.
        flow_tag (str): Choice of either "dev" or "production", to be passed
                        as a --tag to your flow.
        rebuild_base (bool): Whether or not to rebuild the docker image from
                             scratch (starting with Dockerfile-base then
                             Dockerfile). Only do this if you have changed
                             Dockerfile-base.
        rebuild_flow (bool): Whether or not to rebuild the docker image from
                             the base image upwards (only implementing
                             Dockerfile, not Dockerfile-base). This is done by
                             default to include the latest changes to your flow
        flow_kwargs (dict): Keyword arguments to pass to your flow as
                            parameters (e.g. `{'foo':'bar'}` will be passed to
                            the flow as `metaflow example.py run --foo bar`).
        preflow_kwargs (dict): Keyword arguments to pass to metaflow BEFORE the
                               run command (e.g. `{'foo':'bar'}` will be passed
                               to the flow as `metaflow example.py --foo bar run`).
        container_kwargs (dict): Additional keyword arguments to pass to the
                                 docker run command, e.g. mem_limit for setting
                                 the memory limit. See the python-docker docs
                                 for full information.
        requires_task (luigi.Task): Any task that this task is dependent on.
        requires_task_kwargs (dict): Keyword arguments to pass to any dependent
                                     task, if applicable.
    """
    orm = SqlAlchemyParameter()
    flow_path = luigi.Parameter()
    flow_tag = luigi.ChoiceParameter(choices=["dev", "production"],
                                     var_type=str, default="dev")
    rebuild_base = luigi.BoolParameter(default=False)
    rebuild_flow = luigi.BoolParameter(default=True)
    flow_kwargs = luigi.DictParameter(default={})
    preflow_kwargs = luigi.DictParameter(default={})
    container_kwargs = luigi.DictParameter(default={})
    requires_task = luigi.TaskParameter(default=S3PathTask)
    requires_task_kwargs = luigi.DictParameter(default={})

    def requires(self):
        return MetaflowTask(flow_path=self.flow_path,
                            flow_tag=self.flow_tag,
                            rebuild_base=self.rebuild_base,
                            rebuild_flow=self.rebuild_flow,
                            flow_kwargs=self.flow_kwargs,
                            preflow_kwargs=self.preflow_kwargs,
                            container_kwargs=self.container_kwargs,
                            requires_task=self.requires_task,
                            requires_task_kwargs=self.requires_task_kwargs)

    @abc.abstractclassmethod
    def curate_data(self):
        """Retrieves data from the metaflow task.
        Look for the file you need in self.s3path
        then curate the data into list --> dict
        ready for insertion into the database via an ORM.
        """
        pass

    def run(self):
        self.s3path = self.input().open('r').read()
        raise NotImplementedError
        # data = self.curate_data()
        # self.insert_data(self.orm, data)

    def output(self):
        raise NotImplementedError
        # return MySqlTarget
