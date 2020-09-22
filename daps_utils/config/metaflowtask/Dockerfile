FROM metaflowbase:latest

# Copy local file structure, including the local repo
ARG FLOW
ARG FLOWDIR
ARG LAUNCHSH
ARG REPONAME
ARG METAFLOWCONFIG
ARG METAFLOW_RUN_PARAMETERS
ARG METAFLOW_PRERUN_PARAMETERS
ARG METAFLOW_PROFILE
ARG USER

RUN mkdir ~/.metaflowconfig
RUN echo ${METAFLOWCONFIG} > ~/.metaflowconfig/config.json

ENV METAFLOW_PROFILE=${METAFLOW_PROFILE}
ENV USER=${USER}
ENV FLOW=${FLOW}
ENV FLOWDIR=${FLOWDIR}
ENV REPONAME=/tmp/${REPONAME}
ENV METAFLOW_RUN_PARAMETERS=${METAFLOW_RUN_PARAMETERS}
ENV METAFLOW_PRERUN_PARAMETERS=${METAFLOW_PRERUN_PARAMETERS}
ENV PYTHONPATH=/tmp/
COPY . ${REPONAME}

# Set up conda env
RUN conda init bash
RUN exec bash && /bin/bash ~/.bashrc && conda activate metaflow-env

# Install system reqs
RUN ls ${REPONAME}/requirements.txt && /opt/conda/envs/metaflow-env/bin/pip install -r ${REPONAME}/requirements.txt || true

# Move to working directory and install local reqs
RUN /opt/conda/envs/metaflow-env/bin/pip install https://github.com/nestauk/daps_utils/archive/dev.zip --no-cache
RUN ls ${REPONAME}/${FLOWDIR}/requirements.txt && /opt/conda/envs/metaflow-env/bin/pip install -r ${REPONAME}/${FLOWDIR}/requirements.txt || true
RUN conda clean -afy

# Prepare for launch
ADD ${LAUNCHSH} /usr/local/bin/launch.sh
RUN chmod +x /usr/local/bin/launch.sh
WORKDIR /tmp
USER root
ENTRYPOINT ["/usr/local/bin/launch.sh"]
