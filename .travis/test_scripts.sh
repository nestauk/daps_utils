#!/bin/bash

set -e

function SetupDummyDirectory(){
    # Set up directory ready for script testing    
    mkdir ${1}/script-tests &> /dev/null || true
    cd ${1}/script-tests
    mkdir -p ${2}/${2}    
    cd ${2}
    git init .
    git commit --allow-empty -m 'dummy commit'
}

function RunScript(){
    # Try running the script without and with args
    ${2} || ${2} ${2}
}

function ScriptIsInstalled(){
    # Check the script is installed
    if ! command -v ${1} &> /dev/null
    then
	echo "Command '${1}' does not exist. Check setup.py to understand why it hasn't been installed." >&2
	exit 1
    fi
}

# Start
TOPDIR=${PWD}

# For each script, create a dummy directory,
# setup git and run the script
for filepath in ${TOPDIR}/scripts/*; do
    filename=$(basename $filepath)
    echo "#################################################"
    echo -e "###### Running test for ${filename} ######\n" 
    set -x
    ScriptIsInstalled ${filename}
    SetupDummyDirectory ${TOPDIR} ${filename}
    RunScript ${TOPDIR} ${filename}
    rm -rf ${1}/script-tests
    set +x    
    echo -e "\n############ All tests passed #################"
    echo -e "###############################################\n"
done
