"""
@Project: api-auto-test
@File: fixtures.py
@Author: Seeker
@Date: 2023/7/10 12:52 下午
"""
import time

import pytest


@pytest.fixture
def delay3s():
    time.sleep(3)
