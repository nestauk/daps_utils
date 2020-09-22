from importlib import import_module
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect

import logging
import time
import inspect as _inspect  # to avoid namespace clash with sqlalchemy
from .parse_caller import get_main_caller_pkg
CALLER_PKG = get_main_caller_pkg(_inspect.currentframe())


def object_as_dict(obj):
    """Convert a SqlAlchemy object to a python dict representation"""
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


def cast_as_sql_python_type(field, data):
    """Cast the data to ensure that it is the python type expected by SQL

    Args:
        field (SqlAlchemy field): SqlAlchemy field, to cast the data
        data: A data field to be cast
    Returns:
        _data: The data field, cast as native python equivalent of the field.
    """
    _data = field.type.python_type(data)
    if field.type.python_type is str:
        # Include the VARCHAR(n) case
        n = field.type.length if field.type.length < len(_data) else None
        _data = _data[:n]
    return _data


def filter_out_duplicates(data, model, session, low_memory=True):
    """Produce a filtered list of data, exluding duplicates and entries that
    already exist in the data.

    Args:
        data (:obj:`list` of :obj:`dict`): Rows of data to insert
        model (:obj:`sqlalchemy.Base`): The ORM for this data.
        session (:obj:`sqlalchemy.orm.session.Session`): SqlAlchemy session object.
        low_memory (bool): If the pkeys are few or small types (i.e. they won't
                           occupy lots of memory) then set this to True.
                           This will speed things up significantly (like x 100),
                           but will blow up for heavy pkeys or large tables.
    Returns:
        :obj:`list` of :obj:`model` instantiated by data, with dupe pks rm'd.
    """
    # Read all pks if in low_memory mode
    all_pks = set()
    pkey_cols = model.__table__.primary_key.columns
    is_auto_pkey = all(p.autoincrement and p.type.python_type is int
                       for p in pkey_cols)
    if low_memory and not is_auto_pkey:
        fields = [getattr(model, pkey.name) for pkey in pkey_cols]
        all_pks = set(session.query(*fields).all())

    objs = []
    for irow, row in enumerate(data):
        # The data must contain all of the pkeys
        if not is_auto_pkey and not all(pkey.name in row for pkey in pkey_cols):
            raise ValueError(f"{row} does not contain any of {pkey_cols}"
                             f"{[pkey.name in row for pkey in pkey_cols]}")
        # Generate the pkey for this row
        if not is_auto_pkey:
            pk = tuple([cast_as_sql_python_type(pkey, row[pkey.name])
                        for pkey in pkey_cols])
            # The row mustn't aleady exist in the input data
            if pk in all_pks:
                continue
            all_pks.add(pk)
        # Nor should the row exist in the DB (low_memory==False, this is slow)
        if not is_auto_pkey and not low_memory and session.query(exists(model, **row)).scalar():
            continue
        objs.append(model(**row))
    return objs


def insert_data(data, model, session, low_memory=True):
    """
    Convenience method for getting the MySQL engine and inserting
    data into the DB whilst ensuring a good connection is obtained
    and that no duplicate primary keys are inserted.
    Args:
        data (:obj:`list` of :obj:`dict`): Rows of data to insert
        session (:obj:`sqlalchemy.orm.session.Session`): generated session
        model (:obj:`sqlalchemy.Base`): The ORM for this data.
        low_memory (bool): To speed things up significantly, you can read
                           all pkeys into memory first, but this will blow
                           up for heavy pkeys or large tables.

    Returns:
        :obj:`list` of :obj:`model` instantiated by data, with dupe pks rm'd.
    """
    objs = filter_out_duplicates(data=data, model=model,
                                 session=session, low_memory=low_memory)
    session.bulk_save_objects(objs)
    return objs


def try_until_allowed(f, *args, **kwargs):
    '''Keep trying a function if a OperationalError is raised.
    Specifically meant for handling too many
    connections to a database.

    Args:
        f (:obj:`function`): A function to keep trying.
    '''
    while True:
        try:
            value = f(*args, **kwargs)
        except OperationalError:
            logging.warning("Waiting on OperationalError")
            time.sleep(5)
            continue
        else:
            return value


def get_mysql_engine(database="tests"):
    '''Generates the MySQL DB engine for tests

    Args:
        db_env (str): Name of environmental variable
                      describing the path to the DB config.
        section (str): Section of the DB config to use.
        database (str): Which database to use
                        (default is a database called 'production_tests')
    '''
    conf = dict(CALLER_PKG.config['mysqldb']._sections['mysqldb'])
    url = URL(drivername='mysql+pymysql',
              username=conf['user'],
              password=conf.get('password'),
              host=conf.get('host'),
              port=conf.get('port'),
              database=database)
    return create_engine(url, connect_args={"charset": "utf8mb4"})


@contextmanager
def db_session(database="tests"):
    """Creates and mangages an sqlalchemy session.

    Args:
        engine (:obj:`sqlalchemy.engine.base.Engine`): engine to use to access the database

    Returns:
        (:obj:`sqlalchemy.orm.session.Session`): generated session
    """
    engine = get_mysql_engine(database=database)
    Session = try_until_allowed(sessionmaker, engine)
    session = try_until_allowed(Session)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def get_orm_base(orm_name):
    """Get the Base class by ORM name"""
    base = '.'.join((CALLER_PKG.__name__, 'orms', orm_name))
    pkg = import_module(str(base))
    return pkg.Base
