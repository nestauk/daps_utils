"""
flow
-----

Common DAPS flow mixins.
"""
import sys

from metaflow import Parameter


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
    production = Parameter('production',
                           help='Run in production mode?',
                           default=False)

    @property
    def test(self):
        """Opposite of production"""
        return not self.production

    @property
    def db_name(self):
        if "pytest" in sys.modules:  # True if running from pytest
            return 'test'
        return 'dev' if self.test else 'production'
