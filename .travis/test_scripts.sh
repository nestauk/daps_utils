#!/bin/bash

set -e
set -x

function SetupDummyDirectory(){
    mkdir ${1}/script-tests &> /dev/null || true
    cd ${1}/script-tests
    mkdir ${2}/${2}
    cd ${2}
}

function RunScriptTests(){
    bash ${1}/scripts/${2}
    bash ${1}/scripts/tests/${2}
}

# Start
TOPDIR=${PWD}

# For each script, create a dummy directory,
# setup git and run the script
for filename in ${TOPDIR}/scripts/*; do
    SetupDummyDirectory ${TOPDIR} ${filename}
    RunScriptTests ${TOPDIR} ${filename}
done
