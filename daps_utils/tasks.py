"""
tasks
-----

Common DAPS task types.
"""

import abc
import inspect
import json
import re
import sys
from datetime import datetime as dt
from importlib import import_module

import boto3
import luigi
from luigi.contrib.mysqldb import MySqlTarget
from luigi.contrib.s3 import S3PathTask, S3Target
from sqlalchemy_utils.functions import get_declarative_base

from .breadcrumbs import pickup_breadcrumb
from .db import db_session, insert_data
from .docker_utils import build_and_run_image, get_metaflow_config
from .parameters import SqlAlchemyParameter
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


def toggle_force_to_false(func):
    """Toggle self.force permanently to be False. This is required towards
    the end of the task's lifecycle, when we need to know the true value
    of Target.exists()"""

    def wrapper(self, *args, **kwargs):
        self.force = False
        return func(self, *args, **kwargs)
    return wrapper


def toggle_exists(output_func):
    """Patch Target.exists() if self.force is True"""

    def wrapper(self):
        outputs = output_func(self)
        for out in luigi.task.flatten(outputs):
            # Patch Target.exists() to return False
            if self.force:
                out.exists = lambda *args, **kwargs: False
            # "Unpatch" Target.exists() to it's original form
            else:
                out.exists = lambda *args, **kwargs: (
                    out.__class__.exists(out, *args, **kwargs))
        return outputs
    return wrapper


class ForceableTask(luigi.Task):
    """A luigi task which can be forceably rerun"""
    force = luigi.BoolParameter(significant=False, default=False)
    force_upstream = luigi.BoolParameter(significant=False, default=False)

    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force children to be rerun
        if self.force_upstream:
            self.force = True
            children = luigi.task.flatten(self.requires())
            for child in children:
                child.force = True

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.output = toggle_exists(cls.output)
        # Later on in the task's lifecycle, run and trigger_event are called so we can use
        # these as an opportunity to toggle "force = False" to allow the Target.exists()
        # to return it's true value at the end of the Task
        cls.run = toggle_force_to_false(cls.run)
        cls.trigger_event = toggle_force_to_false(cls.trigger_event)


class MetaflowTask(ForceableTask):
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


class CurateTask(ForceableTask, DapsTaskMixin):
    """Run metaflow Flows in Docker, then curate the data
    and store the result in a database table.

    Args:
        model (SqlAlchemy model): A SqlAlchemy ORM, indicating the table
                                  of interest.
        flow_path (str): Path to your flow, relative to the flows directory.
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
    rebuild_base = luigi.BoolParameter(default=False)
    rebuild_flow = luigi.BoolParameter(default=True)
    flow_kwargs = luigi.DictParameter(default={})
    preflow_kwargs = luigi.DictParameter(default={})
    container_kwargs = luigi.DictParameter(default={})
    requires_task = luigi.TaskParameter(default=S3PathTask)
    requires_task_kwargs = luigi.DictParameter(default={})
    low_memory = luigi.BoolParameter(default=True)

    def requires(self):
        return MetaflowTask(flow_path=self.flow_path,
                            flow_tag=self.db_name,
                            rebuild_base=self.rebuild_base,
                            rebuild_flow=self.rebuild_flow,
                            flow_kwargs=self.flow_kwargs,
                            preflow_kwargs=self.preflow_kwargs,
                            container_kwargs=self.container_kwargs,
                            requires_task=self.requires_task,
                            requires_task_kwargs=self.requires_task_kwargs)

    def retrieve_data(self, s3path, file_prefix):
        s3 = boto3.resource('s3')
        S3REGEX = "s3://(.*)/(metaflow/data/.*)"
        bucket_name, prefix = re.findall(S3REGEX, s3path)[0]
        bucket = s3.Bucket(bucket_name)
        obj, = [obj for obj in bucket.objects.filter(
            Prefix=f"{prefix}/{file_prefix}")]
        buffer = obj.get()['Body'].read().decode('utf-8')
        data = json.loads(buffer)
        return data

    @abc.abstractclassmethod
    def curate_data(self, s3_path):
        """Retrieves data from the metaflow task.
        Look for the file you need in self.s3path
        then curate the data into list --> dict
        ready for insertion into the database via an ORM.
        """
        pass

    def run(self):
        self.s3path = self.input().open('r').read()
        data = self.curate_data(self.s3path)
        with db_session(database=self.db_name) as session:
            # Create the table if it doesn't already exist
            engine = session.get_bind()
            Base = get_declarative_base(self.orm)
            Base.metadata.create_all(engine)
            # Insert the data
            insert_data(data, self.orm, session, low_memory=self.low_memory)
        return self.output().touch()

    def output(self):
        conf = CALLER_PKG.config['mysqldb']['mysqldb']
        conf["database"] = self.db_name
        conf["table"] = '[daps-utils]'  # Just a dummy name
        conf.pop('port', None)
        return MySqlTarget(update_id=self.task_id, **conf)


class DapsRootTask(RootTask, DapsTaskMixinBase):
    """
    On top of the DapsTaskMixinBase, this base class includes:

    - A `production` luigi.Parameter by default
    - A `@property` called `test` which returns to opposite of `production`

    Note that the design choice is made for `production` to be a parameter,
    so that running `production=True` is neither the default choice nor
    something that can be run without explicit approval.

    On the other hand it is frequently more convienent in the codebase to make
    exceptions for a `test` mode. For this reason, frequently specifying
    `not production` is clunky and so the `test` property exists for this
    purpose.
    """
    production = luigi.BoolParameter(default=False)

    @property
    def test(self):
        """Opposite of production"""
        return not self.production


class DapsTaskMixin(DapsTaskMixinBase):
    """
    On top of the DapsTaskMixinBase, this base class includes:

    - A `test` luigi.Parameter by default
    - A `@property` called `production` which returns to opposite of `test`
    """
    test = luigi.BoolParameter()

    @property
    def production(self):
        """Opposite of test"""
        return not self.test


class DapsTaskMixinBase:
    """
    Base class for accessing the database name, assuming that
    a property or parameter 'test' as been set.

    The `db_name` parameter is similarly a standard we have long settled with,
    and is an unnecessary source of repetition.
    """
    @property
    def db_name(self):
        if "pytest" in sys.modules:  # True if running from pytest
            return 'test'
        return 'dev' if self.test else 'production'
