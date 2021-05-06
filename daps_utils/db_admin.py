import boto3
from contextlib import contextmanager
import re
from functools import partial
from daps_utils.db import db_session, insert_data, windowed_query

PAGINATION_FIELD = "Marker"
TIME_FORMAT = "%Y-%m-%d"
CREATED_TIME = "SnapshotCreateTime"
EXCESS_SNAPSHOT_FIELDS = [
    "SnapshotCreateTime",
    "AllocatedStorage",
    "Status",
    "InstanceCreateTime",
    "MasterUsername",
    "SnapshotType",
    "KmsKeyId",
    "DBSnapshotArn",
    "DbiResourceId",
    "TagList",
]


class NoSuchSnapshot(Exception):
    pass


def get_snapshots(instance_id):
    rds = boto3.client("rds")
    kwargs = {"DBInstanceIdentifier": instance_id, "SnapshotType": "automated"}
    next_page = ""  # non-None default value
    while next_page is not None:
        response = rds.describe_db_snapshots(**kwargs)
        next_page = response.pop(PAGINATION_FIELD, None)
        for snapshot in response["DBSnapshots"]:
            yield snapshot
        # Setup the next page, if applicable
        kwargs[PAGINATION_FIELD] = next_page


def id_from_hostname(hostname):
    """
    Split out <instance_id>, <uid>.<region>.rds.amazonaws.com
    from <instance_id>.<uid>.<region>.rds.amazonaws.com
    """
    instance_id, _ = re.match(r"(.*?)\.(.*)", hostname).groups()
    return instance_id


def find_snapshot_metadata(hostname, date=None):
    """Finds all snapshot metadata corresponding to the user's database config"""
    instance_id = id_from_hostname(hostname)
    snapshots = get_snapshots(instance_id)
    # Default mode: most recent
    if date is None:
        sorted_snapshots = sorted(snapshots, key=lambda s: s[CREATED_TIME])
        return sorted_snapshots[-1]
    # Otherwise select by date
    snapshots_by_date = {s[CREATED_TIME].strftime(TIME_FORMAT): s for s in snapshots}
    try:
        return snapshots_by_date[date]
    except KeyError:
        raise NoSuchSnapshot(f"Could not find a snapshot for date {date}")


def restore_db(snapshot):
    """Restore a snapshot"""
    rds = boto3.client("rds")
    # Remove or reformat fields in the snaphot info
    # for passing to restore_db_instance_from_db_snapshot
    vpc_id = snapshot.pop("VpcId")
    iam_auth = snapshot.pop("EnableIAMDatabaseAuthentication")
    for field in EXCESS_SNAPSHOT_FIELDS:
        snapshot.pop(field, None)
    # Restore the database
    response = rds.restore_db_instance_from_db_snapshot(
        EnableIAMDatabaseAuthentication=iam_auth,
        VpcSecurityGroupIds=[vpc_id],
        MultiAZ=False,
        PubliclyAccessible=True,
        AutoMinorVersionUpgrade=False,
        DeletionProtection=False,
        **snapshot,
    )
    restored_hostname = response["DBInstance"]["Endpoint"]["Address"]
    return restored_hostname


@contextmanager
def restore_db_from_snapshot(hostname, date=None):
    snapshot_metadata = find_snapshot_metadata(hostname=hostname, date=date)
    snapshot_hostname = restore_db(snapshot_metadata)
    instance_id = id_from_hostname(snapshot_hostname)
    try:
        yield snapshot_hostname
    except:  # Doesn't matter what went wrong: always delete the snapshot DB afterwards!
        pass
    finally:
        rds = boto3.client("rds")
        rds.delete_db_instance(DBInstanceIdentifier=instance_id, SkipFinalSnapshot=True)


def drop_and_recreate(model, session):
    engine = session.get_bind()
    model.__table__.drop(engine)
    model.__table__.create(engine)


def restore_table_from_snapshot_db(model, main_session, backup_session):
    drop_and_recreate(model, main_session)  # Clear table ready for data from snapshot
    # Stream data from the snapshot into the table
    for chunk in windowed_query(model, backup_session):
        insert_data(chunk, model, main_session)


def restore_table_from_snapshot(model, host, database):
    _db_session = partial(db_session, database)
    with restore_db_from_snapshot(host) as snapshot_hostname:
        print(snapshot_hostname)
        with _db_session() as main_db, _db_session(snapshot_hostname) as snapshot_db:
            print(model, main_db, snapshot_db)
            restore_table_from_snapshot_db(model, main_db, snapshot_db)
