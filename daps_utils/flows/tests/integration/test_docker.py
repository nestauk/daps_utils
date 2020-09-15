import pytest

import daps_utils
from daps_utils.docker_utils import logging
from daps_utils.docker_utils import docker
from daps_utils.docker_utils import DockerNamespaceError
from daps_utils.docker_utils import BadDockerfileSetup
from daps_utils.docker_utils import build_and_run_image

logger = logging.basicConfig(level=logging.DEBUG)
BASE_PATH = 'tests/integration/{}/example_flow.py'


def test_good_defaults_full_rebuild():
    flow_path = BASE_PATH.format('good_defaults')
    build_and_run_image(daps_utils, flow_path,
                        rebuild_base=True,
                        rebuild_flow=True)


def test_good_defaults_partial_rebuild():
    flow_path = BASE_PATH.format('good_defaults')
    build_and_run_image(daps_utils, flow_path, rebuild_flow=True)


def test_good_overrides():
    flow_path = BASE_PATH.format('good_overrides')
    build_and_run_image(daps_utils, flow_path,
                        rebuild_base=True,
                        rebuild_flow=True)


def test_bad_namespace_fails():
    flow_path = BASE_PATH.format('bad_namespace')
    with pytest.raises(DockerNamespaceError):
        build_and_run_image(daps_utils, flow_path,
                            rebuild_base=True,
                            rebuild_flow=False)


def test_only_base_given_fails():
    flow_path = BASE_PATH.format('only_base_given')
    with pytest.raises(BadDockerfileSetup):
        build_and_run_image(daps_utils, flow_path,
                            rebuild_base=True,
                            rebuild_flow=False)


def test_bad_base_image_fails():
    flow_path = BASE_PATH.format('bad_base_image')
    with pytest.raises(docker.errors.BuildError):
        build_and_run_image(daps_utils, flow_path,
                            rebuild_base=True,
                            rebuild_flow=False)


def test_bad_flow_Dockerfile_fails():
    flow_path = BASE_PATH.format('bad_flow_Dockerfile')
    with pytest.raises(docker.errors.BuildError):
        build_and_run_image(daps_utils, flow_path,
                            rebuild_base=False,
                            rebuild_flow=True)


def test_bad_flow_launchsh_fails():
    flow_path = BASE_PATH.format('bad_flow_launchsh')
    with pytest.raises(docker.errors.DockerException):
        build_and_run_image(daps_utils, flow_path,
                            rebuild_base=False,
                            rebuild_flow=True)
