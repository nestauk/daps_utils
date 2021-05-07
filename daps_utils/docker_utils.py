"""
docker_utils
------------

Utils for running Docker containers. The primary aim is
to run metaflow Flows.

See :obj:`build_and_run_image` for the main usage.
"""

from metaflow.metaflow_config import METAFLOW_CONFIG
from pathlib import Path
from getpass import getuser
import logging
import docker
import os
import json
import time


class DockerNamespaceError(Exception):
    """Exception when a local Dockerfile-base is given which has tag
    name which is the same as the default Dockerfile-base tag name,
    found under config/metaflowtask/Dockerfile.
    """
    pass


class BadDockerfileSetup(Exception):
    """Exception when a local Dockerfile-base is given, but no
    local Dockerfile is given.
    """
    pass


def get_metaflow_config():
    """Workaround for Travis"""
    k = 'METAFLOW_DATASTORE_SYSROOT_S3'
    if k not in METAFLOW_CONFIG:
        METAFLOW_CONFIG[k] = ''
    return METAFLOW_CONFIG


def base_image_tag(dockerfile):
    """Extract the image tag from the fist line of a dockerfile."""
    with open(dockerfile) as f:
        FROM, IMAGETAG = f.readline().split()  # "FROM IMAGETAG" on first line
    return IMAGETAG


def decode_logs(output):
    """Decode docker log files and append '>>>' to the start of each line."""
    logs = b''.join([line for line in output])
    logs = b'\n'.join(b'>>> %a' % line.decode()
                      for line in logs.split(b'\n'))
    return '\n'+logs.decode()


def _build_image(pkg, tag, rebuild, **kwargs):
    """Call docker SDK to build an image if it doesn't already exist."""
    dkr = docker.from_env()
    logs = []
    try:
        logging.info(f"Retrieving image '{tag}'")
        img = dkr.images.get(tag)
        logging.info(f"Image '{tag}' already exists")
    except docker.errors.ImageNotFound:
        rebuild = True
        logging.info(f"Image '{tag}' not found")
    if rebuild:
        logging.info(f"Building image '{tag}'")
        img, logs = dkr.images.build(path=pkg.__basedir__,
                                     tag=tag,
                                     **kwargs)
    return img, logs


def build_image(pkg, tag, rebuild=False, **kwargs):
    """Call docker SDK to build an image."""
    img, logs = _build_image(pkg, tag, rebuild, **kwargs)
    for log in logs:
        logging.debug(log)
    return img


def fullpath_to_relative(pkg, path):
    """Convert a full path to one relative to the repo root"""
    stub = str(path).replace(pkg.__basedir__, '')
    relative = os.path.join(pkg.__name__, stub)
    return relative


def get_filepath(pkg, flow_dir, filename):
    """Extract a file by name from the flow directory. If the file
    doesn't exist in the flow directory, pick up the default one
    from the config/metaflowtask/ directory.
    """
    flow_dir = os.path.join(pkg.__basedir__, flow_dir)
    if filename in os.listdir(flow_dir):
        fpath = os.path.join(flow_dir, filename)
    else:
        p = Path(filename)
        fpath = pkg.config['metaflowtask'][filename.replace(p.suffix, '')]
    logging.debug(f"Using file '{fpath}'")
    return fpath


def parse_flow_path(flow_path):
    """Parse the relative flow path into three components: the absolute path
    to the flow directory, the name of the flow module, and
    also of the flow module name without the suffix.
    """
    flow_path = 'flows' / Path(flow_path)
    flow_dir = str(flow_path.parent)
    flow_name = flow_path.name
    flow_tag = flow_name.replace(flow_path.suffix, '')
    return flow_dir, flow_name, flow_tag


def build_flow_image(pkg, flow_path, rebuild_base,
                     rebuild_flow, flow_kwargs, preflow_kwargs):
    """Build the base and flow images, and check that
    the dockerfile and namespace setup won't cause obvious clashes."""
    flow_dir, flow_name, tag = parse_flow_path(flow_path)
    dockerfile = get_filepath(pkg, flow_dir, 'Dockerfile')
    using_default = dockerfile == pkg.config['metaflowtask']['Dockerfile']

    # Build the base image, if required
    base_tag = base_image_tag(dockerfile)
    base_dockerfile = get_filepath(pkg, flow_dir,
                                   'Dockerfile-base')

    # Work out whether the user has a namespace clash
    default_base_tag = base_image_tag(pkg.config['metaflowtask']['Dockerfile'])
    using_base = base_dockerfile == pkg.config['metaflowtask']['Dockerfile-base']
    using_base_tag = base_tag == base_image_tag(pkg.config['metaflowtask']['Dockerfile'])
    if using_default and not using_base:
        raise BadDockerfileSetup("If you are using a custom "
                                 "'Dockerfile-base'"
                                 " then you must also use a custom "
                                 "'Dockerfile'.")
    if using_base_tag and not using_base:
        raise DockerNamespaceError('Your "Dockerfile-base" file has '
                                   f'the same tag ("{base_tag}") as the'
                                   f'{pkg.__name__} default.\nHint:\nYour '
                                   '"Dockerfile-base" should start with'
                                   ' something like\n\t'
                                   'FROM amazonlinux:2 AS <something>\n'
                                   'Make sure that <something> is not '
                                   f'"{base_tag}".')
    # Now build the base image
    build_image(pkg=pkg, tag=base_tag, dockerfile=base_dockerfile,
                rebuild=rebuild_base,
                rm=True #  Remove intermediate containers
                ) 

    # Build the flow image
    flow_tag=f'daps_{tag}'
    launchsh = get_filepath(pkg, flow_dir, 'launch.sh')
    build_args = {'METAFLOWCONFIG': json.dumps(METAFLOW_CONFIG),
                  'METAFLOW_RUN_PARAMETERS': ' '.join(f'--{k} {v}' for k, v in
                                                      flow_kwargs.items()),
                  'METAFLOW_PRERUN_PARAMETERS': ' '.join(f'--{k} {v}' for k, v in
                                                         preflow_kwargs.items()),                  
                  'LAUNCHSH': fullpath_to_relative(pkg, launchsh),
                  'REPONAME': pkg.__name__,
                  'USER': getuser(),
                  'FLOWDIR': flow_dir,
                  'FLOW': flow_name}
    rebuild = rebuild_flow or rebuild_base
    build_image(pkg=pkg,
                tag=flow_tag,
                rebuild=rebuild,
                dockerfile=dockerfile,
                nocache=True,
                buildargs=build_args,
                rm=True # Remove intermediate containers
                )
    return flow_tag


def _run(container):
    """Run the given docker container, capture output (regardless of exit
    code), and throw and error if required. The container
    is always cleaned up."""
    container.start()
    logging_driver = container.attrs['HostConfig']['LogConfig']['Type']
    output = container.logs(stdout=True, stderr=True, stream=True, follow=True)
    exit_status = container.wait()['StatusCode']
    logs = decode_logs(output)
    logging.debug(logs)
    container.remove(force=True)
    if exit_status != 0:
        msg = (f"Container failed with exit status {exit_status}.\n",
               "The following trace came from your failed container:", logs)
        raise docker.errors.DockerException('\n'.join(msg))
    logging.debug(f"Container finished with exit code {exit_status}")
    return logs


def run_image(img, **kwargs):
    """Set up AWS credentials for the docker image, then run in
    a new container."""
    dkr = docker.DockerClient(base_url='unix://var/run/docker.sock')
    logging.info(f"Running container on image '{img}'")
    container = dkr.containers.create(img, 
                                        tty=True, 
                        # Enable auto-removal of the container on 
                        # daemon side when the container’s process exits
                                        auto_remove=True,
                                        **kwargs)
    logs = _run(container)
    return logs


def build_and_run_image(pkg, flow_path, rebuild_base=False,
                        rebuild_flow=True, flow_kwargs={},
                        preflow_kwargs={}, **kwargs):
    """Build and run an image for your flow, by specifying
    the relative path to your flow (from the repo base).
    If local Dockerfile, Dockerfile-base and launch.sh are provided,
    then the flow can also have a completely customisable environment
    and runtime behaviour.

    Args:
        flow_path (str): relative path to your flow
        rebuild_base (bool): rebuild the base image?
        rebuild_flow (bool): rebuild the flow image?
        kwargs: All other keyword arguments to pass to docker.containers.create
    """
    flow_tag = build_flow_image(pkg, flow_path, rebuild_base,
                                rebuild_flow, flow_kwargs, preflow_kwargs)
    logs = run_image(flow_tag, **kwargs)
    return logs, flow_tag
