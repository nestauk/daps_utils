FROM metaflowintegration:latest

# Copy local file structure, including the local repo
ARG FLOW
ARG FLOWDIR
ARG LAUNCHSH
ARG REPONAME
ARG METAFLOWCONFIG
ARG USER

RUN mkdir ~/.metaflowconfig
RUN echo ${METAFLOWCONFIG} > ~/.metaflowconfig/config.json

ENV USER=${USER}
ENV FLOW=${FLOW}
ENV FLOWDIR=${FLOWDIR}
ENV REPONAME=/tmp/${REPONAME}
COPY . ${REPONAME}

# Set up conda env
RUN conda init bash
RUN exec bash && /bin/bash ~/.bashrc && conda activate metaflow-env

# Move to working directory and install requirements
RUN /opt/conda/envs/metaflow-env/bin/pip install -r ${REPONAME}/${FLOWDIR}/requirements.txt && conda clean -afy

# Prepare for launch
ADD ${LAUNCHSH} /usr/local/bin/launch.sh
RUN chmod +x /usr/local/bin/launch.sh
WORKDIR /tmp
USER root
ENTRYPOINT ["/usr/local/bin/launch.sh"]
