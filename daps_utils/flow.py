"""
flow
-----

Common DAPS flow mixins.
"""
import sys
from io import StringIO
from metaflow import Parameter, S3, step
from types import SimpleNamespace
from configparser import ConfigParser
from . import db
from . import breadcrumbs

"""A dummy name for stashing the SQL config on S3"""
SQL_CONFIG = "sql_config"


class DapsFlowMixin:
    """
    A base mixin which includes:

    - A `production` metaflow Parameter by default
    - A `@property` called `test` which returns to opposite of `production`
    - A `@property` which infers the MySQL database name ('dev' or
      'production')
      based on the `production` field.

    Note that the design choice is made for `production` to be a parameter,
    so that running `production=True` is neither the default choice nor
    something that can be run without explicit approval.

    On the other hand it is frequently more convienent in the codebase to make
    exceptions for a `test` mode. For this reason, frequently specifying
    `not production` is clunky and so the `test` property exists for this
    purpose.

    The `db_name` parameter is similarly a standard we have long settled with,
    and is an unnecessary source of repetition.
    """

    production = Parameter("production", help="Run in production mode?", default=False)

    def __init_subclass__(cls, **kwargs):
        """Overload the 'start' step to drop the breadcrumb & stash the sql config."""
        super().__init_subclass__(**kwargs)
        cls.start = step(breadcrumbs.drop(cls.start))
        if db.CALLER_PKG is None:
            raise ValueError("CALLER PKG not found")
        # cls._stash_sql_config()

    @property
    def test(self):
        """Opposite of production"""
        return not self.production

    @property
    def db_name(self):
        if "pytest" in sys.modules:  # True if running from pytest
            return "test"
        return "dev" if self.test else "production"

    def db_session(self, database=None):
        """
        A proxy for db.db_session, which:

          a) takes the database from self.db_name
          b) mocks db.CALLER_PKG using the sqldb.config file
             previously stashed on S3 in self._stash_sql_config()
        """
        if database is None:
            database = self.db_name
        # if db.CALLER_PKG is None:
        #     self._mock_caller_pkg()
        return db.db_session(database=database)

    # def _stash_sql_config(self):
    #     """Stash the sql config file on S3 for later"""
    #     # Extract the sql config, formatted as .INI
    #     with StringIO() as sio:
    #         db.CALLER_PKG.config["mysqldb"].write(sio)  # formats as .INI
    #         data = sio.getvalue()
    #     # Stash the sql config file on S3
    #     with S3(run=self) as s3:
    #         s3.put(SQL_CONFIG, data)

    # def _mock_caller_pkg(self):
    #     """
    #     Retrieve the stashed sql config file and assign it to
    #     db.CALLER_PKG.config. In order to do this, db.CALLER_PKG must
    #     be mocked out as e.g. SimpleNamespace() so that setattr
    #     can be called.
    #     """
    #     with S3(run=self) as s3:
    #         data = s3.get(SQL_CONFIG).text
    #     # Read in the config
    #     config = ConfigParser()
    #     config.read_string(data)
    #     # Mock assign the config (formatted as per __initplus__)
    #     # to a dummy caller package in the daps_utils.db namespace
    #     db.CALLER_PKG = SimpleNamespace(config={"mysqldb": config})
