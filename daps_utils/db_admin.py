"""
db admin
--------

Utilities for performing DB admin, such as restoring databases
from a given snapshot.
"""

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


def get_snapshots(instance_id, snapshot_type="automated"):
    """Yield metadata for each RDS snapshot of the given instance ID.

    Args:
        instance_id (str): "DBInstanceIdentifier" described in the RDS docs
        snapshot_type (str): "SnapshotType" described in the RDS docs
    Yields:
        snapshot (dict): Each element of the "DBSnapshots" field of the
                         RDS client's `describe_db_snapshots` method, as described
                         in the RDS docs.
    """
    rds = boto3.client("rds")
    kwargs = {"DBInstanceIdentifier": instance_id, "SnapshotType": snapshot_type}
    next_page = ""  # non-None default value, to kick off the while loop
    while next_page is not None:
        response = rds.describe_db_snapshots(**kwargs)
        next_page = response.pop(PAGINATION_FIELD, None)
        for snapshot in response["DBSnapshots"]:
            yield snapshot
        # Setup the next page's kwargs
        kwargs[PAGINATION_FIELD] = next_page


def id_from_hostname(hostname):
    """
    Split out <instance_id> from <instance_id>.<uid>.<region>.rds.amazonaws.com
    """
    instance_id, _ = re.match(r"(.*?)\.(.*)", hostname).groups()
    return instance_id


def find_snapshot_metadata(hostname, date=None):
    """Finds all snapshot metadata corresponding to given hostname.

    Args:
        hostname (str): Host in the form <instance_id>.<uid>.<region>.rds.amazonaws.com
        date (str): If not specified, the latest snapshot metadata is returned.
                    If specified, formatted according to `TIME_FORMAT`, then
                    the snapshot for this date is returned.
    Returns:
        snapshot (dict): A single snapshot's metadata, either the latest or as specified
    """
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
    """
     Restore a snapshot to a database

     Args:
         snapshot (dict): A single snapshot's metadata.
     Returns:
         restored_hostname (str): The hostname of the restored database.
    ."""
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
        VpcSecurityGroupIds=[vpc_id],  # Can be accessed by same VPC
        MultiAZ=False,  # Not necessary
        PubliclyAccessible=True,  # Can be accessed by IP
        AutoMinorVersionUpgrade=False,  # Not necessary
        DeletionProtection=False,  # Important for allowing automatic deletion!
        **snapshot,
    )
    restored_hostname = response["DBInstance"]["Endpoint"]["Address"]
    return restored_hostname


@contextmanager
def restore_db_from_snapshot(hostname, date=None):
    """
    Restore a database corresponding to a snapshot of a given hostname,
    and then delete the database on exit.

    Args:
        hostname (str): Host of a "main" (non-backup) database, from which snapshots
                        have been take. Expected to be in the form
                        <instance_id>.<uid>.<region>.rds.amazonaws.com
        date (str): If not specified, the latest snapshot metadata is returned.
                    If specified, formatted according to `TIME_FORMAT`, then
                    the snapshot for this date is returned.
    Yields:
        snapshot_hostname (str) The hostname of the restored database
    """
    snapshot_metadata = find_snapshot_metadata(hostname=hostname, date=date)
    restored_hostname = restore_db(snapshot_metadata)
    instance_id = id_from_hostname(restored_hostname)
    try:
        yield restored_hostname
    except:  # Doesn't matter what went wrong: always delete the snapshot DB afterwards!
        pass
    finally:
        rds = boto3.client("rds")
        rds.delete_db_instance(DBInstanceIdentifier=instance_id, SkipFinalSnapshot=True)


def drop_and_recreate(model, session):
    """
    Drop and recreate a table corresponding to the given SqlAlchemy model, for
    a database corresponding to the given session.
    """
    engine = session.get_bind()
    model.__table__.drop(engine)
    model.__table__.create(engine)


def restore_table_from_snapshot_db(model, main_session, backup_session):
    """
    Transfer data to the "main" database from the "backup" database,
    for the table corresponding to the given SqlAlchemy model.

    Args:
        model (SqlAlchemy.Base): A SqlAlchemy ORM
        main_session (SqlAlchemy.Session): A session corresponding to the "main" DB
        backup_session (SqlAlchemy.Session): A session corresponding to the "backup" DB
    """
    drop_and_recreate(model, main_session)  # Clear table ready for data from snapshot
    # Stream data from the snapshot into the table
    for chunk in windowed_query(model, backup_session):
        insert_data(chunk, model, main_session)


def restore_table_from_snapshot(model, hostname, database):
    """
    Restore a specific table to that of the latest snapshot.

    Args:
        model (SqlAlchemy.Base): A SqlAlchemy ORM
        hostname (str): Host of a "main" (non-backup) database, from which snapshots
                        have been take. Expected to be in the form
                        <instance_id>.<uid>.<region>.rds.amazonaws.com
        database (str): Name of the MySQL database (normally "production" or "dev")
    """
    _db_session = partial(db_session, database)
    with restore_db_from_snapshot(hostname) as snapshot_hostname:
        with _db_session() as main_db, _db_session(snapshot_hostname) as snapshot_db:
            restore_table_from_snapshot_db(model, main_db, snapshot_db)
