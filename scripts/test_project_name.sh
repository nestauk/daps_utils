#!/bin/bash -x
set -e

# Run through a test project with calver-init and pyproject.toml naming
# writes to CWD

_TestVersion() {
    [[ $(cat "$1"/VERSION | cut -d'.' -f 4) = "$2" ]]
    return
}

_FirstBranch() {
    git init
    touch testfile
    git add testfile
    git commit -m "first commit"
    echo RUNNING CALVER-INIT
    calver-init
    git add install.sh .githooks/pre-commit .gitconfig .gitattributes
    git commit -m "calver init run"
    git checkout -b testbranch
    touch testfile2
    git add testfile2
    git commit -m "feature commit"
    echo SHOULD BE testbranch
    cat "$1"/VERSION
    echo ""
    _TestVersion "$1" "testbranch"
    return
}

_SecondBranch() {
    git checkout -b testbranch2
    touch testfile3
    git add testfile3
    git commit -m "feature commit 2"
    echo SHOULD BE testbranch2
    cat "$1"/VERSION
    echo ""
    _TestVersion "$1" "testbranch2"
    return
}

echo '*** DIR NAME TEST CASE ***'
rm -Rf testrepo_dirname
mkdir testrepo_dirname
cd testrepo_dirname
_FirstBranch "testrepo_dirname"
_SecondBranch "testrepo_dirname"
echo "TEST SUCCESS"
cd ..

echo '*** PYPROJECT NAME TEST CASE ***'
rm -Rf testrepo_pyproject
mkdir testrepo_pyproject
cd testrepo_pyproject
echo '[tool.poetry]' >> pyproject.toml
echo 'name = "data_utils"' >> pyproject.toml
_FirstBranch "data_utils"
_SecondBranch "data_utils"
echo "TEST SUCCESS"
cd ..

rm -Rf testrepo_dirname
rm -Rf testrepo_pyproject
echo "ALL TESTS SUCCEEDED"
