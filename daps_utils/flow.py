"""
flow
-----

Common DAPS flow mixins.
"""
import sys
from metaflow import Parameter, step
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
        return db.db_session(database=database)
