#!/bin/bash

set -e
ls noneexistentfile
source activate metaflow-env
time python ${REPONAME}/${FLOWDIR}/${FLOW} --no-pylint
