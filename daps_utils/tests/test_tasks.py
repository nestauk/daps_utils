"""
test_tasks
==========

Tests for tasks.py.
"""

from unittest import mock

from daps_utils.tasks import luigi, ForceableTask

# Note that toggle_force_to_false, toggle_exists are
# tested under the ForceableTask tests, since it's very hard
# to write transparent tests for class method decorators
#from daps_utils.tasks import toggle_force_to_false, toggle_exists


PATH = "daps_utils.tasks.{}"


class MockTarget(mock.MagicMock):
    """Need to define a concrete 'exists' method so that
    the __class__ also has the 'exists' method to fall
    back on when toggle_force_to_false is called"""
    def exists(self):
        return True


class MockTask(ForceableTask):
    """'abc' will yield four tasks: 'abc', plus 'a', 'b' and 'c'.
    If "abcd" if specified then the output of task "d" will
    yield AttributeError on calling "remove",
    """
    name = luigi.Parameter(default="abc")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out = MockTarget()

    def output(self):
        return self.out

    def run(self):
        pass

    def trigger_event(self):
        pass

    def other_function(self):
        pass

    def requires(self):
        """'abc' yields 'a', 'b' and 'c'"""
        if len(self.name) > 1:
            for char in self.name:
                yield MockTask(name=char)


@mock.patch(PATH.format("luigi.task.flatten"),
            side_effect=lambda x: [x])
def test_run_affects(mock_flatten):
    """Test that output() will toggle exists() to False,
    and then run() toggles it back"""
    task = MockTask(name='abc', force=True)
    # Originally the output actually exists
    assert task.out.exists() is True
    # output() toggles exists() to False
    assert task.output().exists() is False
    # run() toggles force to False, which toggles exists() to True
    task.run()
    assert task.output().exists() is True


@mock.patch(PATH.format("luigi.task.flatten"),
            side_effect=lambda x: [x])
def test_run_no_force_no_effect(mock_flatten):
    """Test that no toggling takes place when force is False"""
    task = MockTask(name='def', force=False)
    # Originally the output actually exists
    assert task.out.exists() is True
    # output() doesn't toggle exists()
    assert task.output().exists() is True
    # again, shouldn't change anything
    task.run()
    assert task.output().exists() is True


@mock.patch(PATH.format("luigi.task.flatten"),
            side_effect=lambda x: [x])
def test_trigger_event_affects(mock_flatten):
    """Test that output() will toggle exists() to False,
    and then trigger_event() toggles it back"""
    task = MockTask(name='ghi', force=True)
    # Originally the output actually exists
    assert task.out.exists() is True
    # output() toggles exists() to False
    assert task.output().exists() is False
    # trigger_event() toggles force to False, which toggles exists() to True
    task.trigger_event()
    assert task.output().exists() is True


@mock.patch(PATH.format("luigi.task.flatten"),
            side_effect=lambda x: [x])
def test_other_function_doesnt_affect(mock_flatten):
    """Test that output() will toggle exists() to False,
    and then other_function() DOESN'T toggle it back"""
    task = MockTask(name='jkl', force=True)
    # Originally the output actually exists
    assert task.out.exists() is True
    # output() toggles exists() to False
    assert task.output().exists() is False
    # trigger_event() toggles force to False, which toggles exists() to True
    task.other_function()
    assert task.output().exists() is False


@mock.patch(PATH.format("luigi.task.flatten"),
            side_effect=lambda x: [x] if isinstance(x, MockTarget) else x)
def test_force_upstream(mock_flatten):
    """Test that output() will toggle exists() to False,
    and then run() toggles it back, for all children also when
    force_upstream is True"""
    task = MockTask(name='mno', force_upstream=True)
    children = list(task.requires())
    assert len(children) == 3
    assert task.out.exists() is True
    assert task.force is True
    assert task.output().exists() is False
    for child in children:
        assert child.out.exists() is True
        assert child.force is True
        assert child.output().exists() is False
        child.run()
        assert child.output().exists() is True
