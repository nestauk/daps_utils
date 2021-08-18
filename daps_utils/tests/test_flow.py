from unittest import mock

from daps_utils import DapsFlowMixin
from daps_utils.flow import SQL_CONFIG


def test_modes_test():
    class MyFlow(DapsFlowMixin):
        pass

    MyFlow.production = False
    flow = MyFlow()
    assert not flow.production
    assert flow.test


def test_modes_production():
    class MyFlow(DapsFlowMixin):
        pass

    MyFlow.production = True
    flow = MyFlow()
    assert flow.production
    assert not flow.test


def test_db_test_actual_test():
    class MyFlow(DapsFlowMixin):
        pass

    for value in (True, False):
        MyFlow.production = value
        flow = MyFlow()
        assert flow.db_name == "test"


@mock.patch("daps_utils.flow.sys")
def test_db_test_override_sys_production(mocked_sys):
    mocked_sys.modules = []

    class MyFlow(DapsFlowMixin):
        pass

    MyFlow.production = True
    flow = MyFlow()
    assert flow.db_name == "production"


@mock.patch("daps_utils.flow.sys")
def test_db_test_override_sys_dev(mocked_sys):
    mocked_sys.modules = []

    class MyFlow(DapsFlowMixin):
        pass

    MyFlow.production = False
    flow = MyFlow()
    assert flow.db_name == "dev"


@mock.patch.object(DapsFlowMixin, "_mock_caller_pkg")
@mock.patch("daps_utils.flow.db")
def test_db_session_with_caller_pkg(mocked_db, mocked__mock_caller_pkg):
    # Mock up the enviroment
    mocked_db.CALLER_PKG = "not None"
    mocked_db.db_session.side_effect = lambda database=None: database
    # Fire up an instance and exec the function
    flow = DapsFlowMixin()
    assert flow.db_session(database="foo") == "foo"  # lambda x: x
    # Verify that _mock_caller_pkg has not been called
    assert mocked__mock_caller_pkg.call_count == 0


@mock.patch.object(DapsFlowMixin, "_mock_caller_pkg")
@mock.patch("daps_utils.flow.db")
def test_db_session_no_caller_pkg(mocked_db, mocked__mock_caller_pkg):
    # Mock up the enviroment
    mocked_db.CALLER_PKG = None
    mocked_db.db_session.side_effect = lambda database=None: database
    # Fire up an instance and exec the function
    flow = DapsFlowMixin()
    assert flow.db_session(database="foo") == "foo"  # lambda x: x
    # Verify that _mock_caller_pkg has been called
    assert mocked__mock_caller_pkg.call_count == 1


@mock.patch.object(DapsFlowMixin, "_stash_sql_config")
@mock.patch("daps_utils.flow.db")
def test_set_caller_pkg(mocked_db, mocked__stash_sql_config):
    # Fire up an instance and exec the function
    flow = DapsFlowMixin()
    flow.set_caller_pkg(pkg="foo")
    # Verify that CALLER_PKG has been set, and the config has been stashed
    assert mocked_db.CALLER_PKG == "foo"  # lambda x: x
    assert mocked__stash_sql_config.call_count == 1


@mock.patch("daps_utils.flow.S3")
@mock.patch("daps_utils.flow.db")
def test__stash_sql_config(mocked_db, mocked_S3):
    # Mock up the enviroment
    mocked_config = mock.Mock()
    mocked_config.write.side_effect = lambda sio: sio.write("foo")
    mocked_db.CALLER_PKG.config = {"mysqldb": mocked_config}
    # Fire up an instance and exec the function
    flow = DapsFlowMixin()
    flow._stash_sql_config()
    # Verify that s3.put had the correct args
    (filename, data), _ = mocked_S3().__enter__().put.call_args
    assert filename == SQL_CONFIG
    assert data == "foo"


@mock.patch("daps_utils.flow.S3")
@mock.patch("daps_utils.flow.db")
def test__mock_caller_pkg(mocked_db, mocked_S3):
    # Mock up the enviroment
    mocked_S3().__enter__().get().text = "[foo]\n\nbar=baz\n"
    # Fire up an instance and exec the function
    flow = DapsFlowMixin()
    flow._mock_caller_pkg()
    # Verify that CALLER_PKG has been mocked
    assert mocked_db.CALLER_PKG.config["mysqldb"]._sections["foo"] == {"bar": "baz"}
