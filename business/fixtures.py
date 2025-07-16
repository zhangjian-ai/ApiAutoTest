import pytest

from framework.logger import log

"""
实现会用例级别的前后置操作，此处实现夹具与在conftest中实现无差别，可以使用系统内置其他夹具作为参数，来获取用例相关信息
使用家具，直接在用例的 meta.fixtures例表中申明即可
"""


@pytest.fixture(autouse=True)
def demo():
    log.info("before")
    yield
    log.info("after")
