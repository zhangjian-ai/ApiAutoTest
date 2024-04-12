import pytest

from framework.open.logger import log


@pytest.fixture(autouse=True)
def print_demo():
    log.info("test start ...")
    yield
    log.info("test end ...")
