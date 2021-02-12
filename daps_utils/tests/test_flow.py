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
