import os
import pexpect
import pytest
import shutil
import sys
import tempfile
import time

from eplitefrontend import epliteapi


@pytest.yield_fixture(scope="module")
def tempdir():
    # use /run/shm as tempdir because it is usually mounted as tmpfs
    if os.path.isdir("/run/shm"):
        tempfile.tempdir = "/run/shm"

    tempdir = tempfile.mkdtemp(suffix="epliteapi-test")

    yield tempdir

    shutil.rmtree(tempdir)


@pytest.yield_fixture(scope="module")
def etherpad_lite(tempdir):
    srcdir = os.path.join(os.path.dirname(__file__), "..", "etherpad-lite")
    targetdir = os.path.join(tempdir, "etherpad-lite")

    shutil.copytree(srcdir, targetdir)

    testdatadir = os.path.join(os.path.dirname(__file__), "test-data")
    shutil.copy(os.path.join(testdatadir, "epliteapi", "settings.json"),
                targetdir)
    shutil.copy(os.path.join(testdatadir, "epliteapi", "APIKEY.txt"),
                targetdir)

    oldcwd = os.getcwd()
    os.chdir(targetdir)

    process = pexpect.spawn(["./bin/run.sh"], logfile=sys.stdout)

    os.chdir(oldcwd)

    process.expect(["^.*You can access your Etherpad instance at .*$"])

    yield process

    process.terminate()
    for i in xrange(5):
        if process.isalive():
            time.sleep(1)
            continue
        else:
            return
    process.terminate(force=True)
    shutil.rmtree(targetdir1)


@pytest.fixture
def ep(etherpad_lite):
    return epliteapi.EtherpadLiteAPI("http://localhost:9001")


def test_connectivity(ep):
    response = ep.get("/")
    assert response.status_code == 200
