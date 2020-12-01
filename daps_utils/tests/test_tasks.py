from unittest import mock
import pytest

from daps_utils.tasks import luigi
from daps_utils.tasks import prune_outputs

class MockTask(luigi.Task):
    """'abc' will yield four tasks: 'abc', plus 'a', 'b' and 'c'.
    If "abcd" if specified then the output of task "d" will 
    yield AttributeError on calling "remove",
    """
    name = luigi.Parameter(default="abc")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        
        self.out = mock.Mock()
        # Edge-case: output of "d" will yield AttributeError
        if self.name == 'd':
            self.out.remove.side_effect = AttributeError
    def output(self):
        return self.out
    def requires(self):
        if len(self.name) > 1:
            for char in self.name:
                yield MockTask(name=char)


def test_prune_outputs():
    # Root task should have been removed
    task = MockTask()
    prune_outputs(task, force_upstream=True)
    total_outputs = 0
    total_exists_calls = 0
    total_remove_calls = 0
    for out in luigi.task.flatten(task.output()):
        total_outputs += 1
        total_exists_calls += out.exists.call_count
        total_remove_calls += out.remove.call_count
    assert total_outputs == 1
    assert total_exists_calls == 1
    assert total_remove_calls == 1


    # Children should not have been called
    children = luigi.task.flatten(task.requires())
    total_outputs = 0
    total_exists_calls = 0
    total_remove_calls = 0
    for child in children:
        for out in luigi.task.flatten(child.output()):
            total_outputs += 1
            total_exists_calls += out.exists.call_count
            total_remove_calls += out.remove.call_count
    assert len(children) == 3
    assert total_outputs == 3
    assert total_exists_calls == 3
    assert total_remove_calls == 3


def test_prune_outputs_bad_output():
    task = MockTask('abcd')
    with pytest.raises(NotImplementedError):
        prune_outputs(task, force_upstream=True)


def test_prune_outputs_no_upstream():
    # Root task should have been removed
    task = MockTask('xyz')
    prune_outputs(task, force_upstream=False)
    total_outputs = 0
    total_exists_calls = 0
    total_remove_calls = 0
    for out in luigi.task.flatten(task.output()):
        total_outputs += 1
        total_exists_calls += out.exists.call_count
        total_remove_calls += out.remove.call_count
    assert total_outputs == 1
    assert total_exists_calls == 1
    assert total_remove_calls == 1


    # Children should not have been called
    children = luigi.task.flatten(task.requires())
    total_outputs = 0
    total_exists_calls = 0
    total_remove_calls = 0
    for child in children:
        for out in luigi.task.flatten(child.output()):
            total_outputs += 1
            total_exists_calls += out.exists.call_count
            total_remove_calls += out.remove.call_count
    assert len(children) == 3
    assert total_outputs == 3
    assert total_exists_calls == 0
    assert total_remove_calls == 0
