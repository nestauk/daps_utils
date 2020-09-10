import daps_utils
from daps_utils import __basedir__
from daps_utils import __name__ as REPONAME
from daps_utils import config
from daps_utils.docker_utils import base_image_tag
from daps_utils.docker_utils import decode_logs
from daps_utils.docker_utils import fullpath_to_relative

CONFIG = config['metaflowtask']

def test_base_image_tag():
    base_image_tag(CONFIG['Dockerfile']) == 'metaflowbase:latest'


def test_decode_logs():
    msg = 'thisissome\noutput'
    msg = [x.encode() for x in list(msg)]
    expected = "\n>>> 'thisissome'\n>>> 'output'"
    print(repr(expected))
    print(repr(decode_logs(msg)))
    assert decode_logs(msg) == expected


def test_fullpath_to_relative():
    assert fullpath_to_relative(daps_utils, __basedir__) == f'{REPONAME}/'
