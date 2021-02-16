from unittest import mock

from daps_utils import DapsFlowMixin


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
        assert flow.db_name == 'test'


@mock.patch('daps_utils.flow.sys')
def test_db_test_override_sys_production(mocked_sys):
    mocked_sys.modules = []
    class MyFlow(DapsFlowMixin):
        pass
    MyFlow.production = True
    flow = MyFlow()
    assert flow.db_name == 'production'


@mock.patch('daps_utils.flow.sys')
def test_db_test_override_sys_dev(mocked_sys):
    mocked_sys.modules = []
    class MyFlow(DapsFlowMixin):
        pass
    MyFlow.production = False
    flow = MyFlow()
    assert flow.db_name == 'dev'
