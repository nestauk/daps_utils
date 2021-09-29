#!/usr/bin/env python
"""project_name.py

Work out the name of the python project for calver-init's pre-commit hook by looking
for a name in pyproject.toml if it exists, or else deferring to the directory name.

Usage: project_name.py dir

Where dir is a path to the root path to the project."""
import pathlib
import sys


def _parent_dir(input_path):
    """Return parent directory for input path, if it isn't a dir already."""
    while not input_path.is_dir():
        input_path = input_path.parent
    return input_path


def _cli(input_str):
    input_path = _parent_dir(pathlib.Path(input_str).resolve())
    # one could have other places to look perhaps
    toml_path = input_path / "pyproject.toml"
    if toml_path.exists():
        # let's try to pull the name out of toml
        import toml

        pyproject = toml.load(toml_path)
        try:
            return pyproject["tool"]["poetry"]["name"]
        except KeyError:
            print(f"no tool.poetry.name field found in {toml_path}")
    # let's revert to the directory name
    return input_path.name


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("ERROR: unrecognised input\n")
        print(__doc__)
        sys.exit(1)
    sys.stdout.write(_cli(sys.argv[-1]) + "\n")
