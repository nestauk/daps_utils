#!/bin/bash

set -e
source activate metaflow-env
time python ${REPONAME}/${FLOWDIR}/${FLOW} ${METAFLOW_PRERUN_PARAMETERS} --no-pylint run ${METAFLOW_RUN_PARAMETERS}
