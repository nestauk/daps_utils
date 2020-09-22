"""
parse_caller
============

Tool for getting ahold of the module ("package") that makes the first
import of daps_utils. This introspection is required so that
MetaflowTask knows where to find the base directory for finding flows,
config and also the root for building the docker image.
"""

from pathlib import Path
import inspect
import os
from importlib import import_module
import git


class NotSetupProperlyError(Exception):
    pass


def get_git_root(path):
    """From the given path, return the Git repo root dir"""
    git_repo = git.Repo(path, search_parent_directories=True)
    git_root = git_repo.git.rev_parse("--show-toplevel")
    return Path(git_root)


def is_metaflowtask_init_dir(path):
    """Does the given path contain __init__.py and __initplus__.py?"""
    p = Path(path)
    if p.is_dir():
        files = [child.name for child in p.iterdir() if child.is_file()]
        if '__init__.py' in files and '__initplus__.py' in files:
            return True
    return False


def get_pkg_source(path, caller, git_root):
    """Recursively find the directory between the caller and the Git root
    which contains __init__.py and __initplus__.py files. The result is the
    module root path."""
    p = Path(path)
    if is_metaflowtask_init_dir(p):
        return p.name
    if path != git_root:
        return get_pkg_source(p.parent, caller=caller, git_root=git_root)
    raise NotSetupProperlyError(f'Could not find a package for "{caller}." '
                                f'In other words, starting from "{caller}"'
                                ', there were no parent directories '
                                'containing both "__init__.py" and '
                                '"__initplus__.py", which would have been '
                                'expected if this package had been set up '
                                'using the "metaflowtask-init".')


def get_caller(f, ignore=['daps_utils/tasks.py', 'daps_utils/__init__.py',
                          'daps_utils/db.py']):
    """Get the full path to the namespace where daps_utils is first imported
    in runtime. Note that that introspection tool finds a bunch 
    of "frozen" imports (which are artefacts of the python import system, 
    and should be ignored) and then finds two files ('daps_utils/tasks.py', 
    'daps_utils/__init__.py') which are called when daps_utils is imported.
    It is therefore the file following these which is the true "caller".
    """
    fpath = inspect.getfile(f)
    skip = fpath.startswith('<frozen') or any(i in fpath for i in ignore)
    if skip and f.f_back is not None:
        return get_caller(f.f_back)
    return Path(fpath).resolve()


def get_main_caller_pkg(frame):
    """Retrieve the module which called daps_utils first."""
    caller = get_caller(frame)
    # Exception for setup.py
    if caller.name == 'setup.py':
        return None
    # Exception for dockerized flows
    _caller = str(caller)
    if '/flows/' in _caller and _caller.startswith('/tmp/'):
        return None
    # Exception for metaflow flows run from AWS batch
    if _caller.startswith('/metaflow/'):
        return None
    # Exception for users who don't want to use metaflowtask
    try:
        git_root = get_git_root(caller)
    except git.exc.NoSuchPathError:
        return None
    # Otherwise, resolve the calling package
    pkg_name = get_pkg_source(caller, caller, git_root)
    pkg = import_module(pkg_name)
    return pkg
