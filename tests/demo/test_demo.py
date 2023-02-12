import pytest

from utils.common import rewrite


@pytest.mark.smoke
@rewrite()
def test_demo_01():
    """演示用例"""
    pass


@pytest.mark.smoke
@rewrite()
def test_demo_02():
    """参数化演示用例"""
    pass


@pytest.mark.smoke
@rewrite()
def test_demo_03():
    """演示用例"""
    pass


