from unittest import mock
import pytest
from functools import partial
from datetime import datetime as dt
from daps_utils.db_admin import (
    get_snapshots,
    id_from_hostname,
    find_snapshot_metadata,
    restore_db,
    restore_db_from_snapshot,
    drop_and_recreate,
    restore_table_from_snapshot_db,
    restore_table_from_snapshot,
    PAGINATION_FIELD,
    CREATED_TIME,
    NoSuchSnapshot,
    EXCESS_SNAPSHOT_FIELDS,
)

PATH = "daps_utils.db_admin.{}"
boto_patch = partial(mock.patch, PATH.format("boto3"))


@boto_patch()
def test_get_snapshots(mocked_boto):
    n_pages = 11
    snapshots = [123, 345]
    responses = []
    for i in range(n_pages - 1):
        responses.append({PAGINATION_FIELD: i, "DBSnapshots": snapshots})
    responses.append({"DBSnapshots": snapshots})  # 11 pages
    _responses = iter(responses)
    rds = mocked_boto.client()
    rds.describe_db_snapshots.side_effect = lambda **kws: next(_responses)
    all_snapshots = list(get_snapshots("1234"))
    assert all_snapshots == snapshots * 11


def test_id_from_hostname():
    for instance_id in ["ABC", "ABCD", "ABCDE"]:
        hostname = f"{instance_id}.1234.eu-west-1.rds.amazonaws.com"
        assert id_from_hostname(hostname) == instance_id


@mock.patch(PATH.format("get_snapshots"))
def test_find_snapshot_metadata(mocked_get_snapshots):
    fmt = "%Y-%m"
    snapshots = [
        {CREATED_TIME: dt.strptime(created_time, fmt)}
        for created_time in ["2019-01", "2012-01", "2019-10", "2001-12"]
    ]
    mocked_get_snapshots.return_value = snapshots

    # Trial default mode: should be most recent
    snapshot = find_snapshot_metadata("DUMMY.HOSTNAME", date=None)
    assert snapshot[CREATED_TIME].strftime(fmt) == "2019-10"

    # Trial selection mode
    snapshot = find_snapshot_metadata("DUMMY.HOSTNAME", date="2012-01-01")
    assert snapshot[CREATED_TIME].strftime(fmt) == "2012-01"

    # Check raises if no such date
    with pytest.raises(NoSuchSnapshot):
        find_snapshot_metadata("DUMMY.HOSTNAME", date="2021-02-01")


@boto_patch()
def test_restore_db(mocked_boto):
    snapshot = {
        "VpcId": "123",
        "EnableIAMDatabaseAuthentication": "abc",
        "bonus_field_1": "1234",
        "bonus_field_2": "abcd",
    }
    for field in EXCESS_SNAPSHOT_FIELDS:
        snapshot[field] = field  # dummy

    rds = mocked_boto.client()
    _restore_db = rds.restore_db_instance_from_db_snapshot
    _restore_db.return_value = {"DBInstance": {"Endpoint": {"Address": "my house"}}}

    assert restore_db(snapshot) == "my house"
    (_, kwargs) = _restore_db.call_args
    assert kwargs == {
        "EnableIAMDatabaseAuthentication": "abc",
        "VpcSecurityGroupIds": ["123"],
        "MultiAZ": False,
        "PubliclyAccessible": True,
        "AutoMinorVersionUpgrade": False,
        "DeletionProtection": False,
        "bonus_field_1": "1234",
        "bonus_field_2": "abcd",
    }


@boto_patch()
@mock.patch(PATH.format("find_snapshot_metadata"), return_value=None)
@mock.patch(PATH.format("restore_db"), return_value="something")
@mock.patch(PATH.format("id_from_hostname"), return_value=None)
def test_restore_db_from_snapshot(mocked_id, mocked_db, mocked_find, mocked_boto):
    rds = mocked_boto.client()
    with restore_db_from_snapshot("DUMMY") as snapshot_hostname:
        assert snapshot_hostname == "something"
        assert rds.delete_db_instance.call_args is None
    # i.e. delete called after context is closed
    assert rds.delete_db_instance.call_args is not None


def test_drop_and_recreate():
    model = mock.MagicMock()
    model.__table__ = mock.Mock()
    session = mock.Mock()
    drop_and_recreate(model, session)
    assert session.get_bind.call_args is not None
    assert model.__table__.drop.call_args is not None
    assert model.__table__.create.call_args is not None


@mock.patch(PATH.format("drop_and_recreate"))
@mock.patch(PATH.format("windowed_query"))
@mock.patch(PATH.format("insert_data"))
def test_restore_table_from_snapshot_db(mocked_insert, mocked_query, mocked_drop):
    mocked_query.return_value = range(123)
    restore_table_from_snapshot_db(None, None, None)
    assert mocked_insert.call_count == 123


@mock.patch(PATH.format("restore_db_from_snapshot"))
@mock.patch(PATH.format("db_session"))
@mock.patch(PATH.format("restore_table_from_snapshot_db"))
def test_restore_table_from_snapshot(mocked_rest_db, mocked_sess, mocked_rest_table):
    mocked_rest_table().__enter__.return_value = "the snapshot"
    mocked_sess().__enter__.return_value = "a host"
    restore_table_from_snapshot("a model", "the host", "some database")
    (args, _) = mocked_rest_db.call_args
    assert args == ("a model", "a host", "a host")
