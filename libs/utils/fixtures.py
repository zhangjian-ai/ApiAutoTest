import time

import pytest


@pytest.fixture
def delay3s():
    time.sleep(3)
