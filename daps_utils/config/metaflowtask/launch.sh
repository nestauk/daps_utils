#!/bin/bash

set -e
source activate metaflow-env
time python ${REPONAME}/${FLOWDIR}/${FLOW} --no-pylint run ${METAFLOW_RUN_PARAMETERS}
