from pathlib import Path
import inspect
import os
from importlib import import_module
import git


class NotSetupProperlyError(Exception):
    pass


def get_git_root(path):
    git_repo = git.Repo(path, search_parent_directories=True)
    git_root = git_repo.git.rev_parse("--show-toplevel")
    return Path(git_root)


def is_metaflowtask_init_dir(path):
    p = Path(path)
    if p.is_dir():
        files = [child.name for child in p.iterdir() if child.is_file()]
        if '__init__.py' in files and '__initplus__.py' in files:
            return True
    return False


def get_pkg_source(path, caller, git_root):
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


def get_caller(f, ignore=['daps_utils/tasks.py', 'daps_utils/__init__.py']):
    fpath = inspect.getfile(f)
    skip = fpath.startswith('<frozen') or any(i in fpath for i in ignore)
    if skip and f.f_back is not None:
        return get_caller(f.f_back)
    return Path(fpath)


def get_main_caller_pkg(frame):
    caller = get_caller(frame)
    git_root = get_git_root(caller)
    pkg_name = get_pkg_source(caller, caller, git_root)
    pkg = import_module(pkg_name)
    return pkg
