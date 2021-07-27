from unittest import mock
import daps_utils
from daps_utils import __basedir__
from daps_utils import __name__ as REPONAME
from daps_utils import config
from daps_utils.docker_utils import base_image_tag
from daps_utils.docker_utils import decode_logs
from daps_utils.docker_utils import fullpath_to_relative
from daps_utils.docker_utils import get_s3_bucket_key
from daps_utils.docker_utils import truncate_logs
from daps_utils.docker_utils import format_logs
from daps_utils.docker_utils import remove_ansi

CONFIG = config["metaflowtask"]
PATH = "daps_utils.docker_utils.{}"


def test_base_image_tag():
    base_image_tag(CONFIG["Dockerfile"]) == "metaflowbase:latest"


@mock.patch(PATH.format("get_metaflow_config"))
def test_get_s3_bucket_key(mocked_mf_conf):
    mocked_mf_conf.return_value = {"METAFLOW_DATASTORE_SYSROOT_S3": "s3://foo/bar"}
    bucket, key = get_s3_bucket_key("123")
    assert bucket == "foo"
    assert key == "bar/failure-logs/123/logs.txt"


@mock.patch(PATH.format("get_s3_bucket_key"))
def test_truncate_logs(mocked_s3_bkt_key):
    mocked_s3_bkt_key.return_value = "abc", "123"
    logs = [b"first", b"second", b"third", b"fourth", b"fifth", b"sixth", b"seventh"]
    logs = truncate_logs(logs, 4, "dummy_timestamp")
    assert logs == [
        b"See full logs at https://s3.console.aws.amazon.com/s3/object/abc?prefix=123\n",
        b"first",
        b"second",
        b"... truncated ...\n",
        b"sixth",
        b"seventh",
    ]


@mock.patch(PATH.format("boto3"))
@mock.patch(PATH.format("truncate_logs"))
def test_decode_logs(mocked_trunc, mocked_boto3):
    msg = "thisissome\noutput"
    msg = [x.encode() for x in list(msg)]
    expected = "\n>>> 'thisissome'\n>>> 'output'"
    assert decode_logs(msg) == expected


def test_fullpath_to_relative():
    assert fullpath_to_relative(daps_utils, __basedir__) == f"{REPONAME}/"


def test_remove_ansi():
    test_text = b"\x1b[00m\x1b[01;31mexamplefile.zip\x1b[00m\x1b[01;31m"
    assert remove_ansi(test_text) == b"examplefile.zip"


def integration_decode_logs():
    logs = [
        b"first\n",
        b"second\n",
        b"third\n",
        b"fourth\n",
        b"fifth\n",
        b"sixth\n",
        b"seventh\n",
    ]
    output = decode_logs(logs, max_lines=4)
    print(output)
