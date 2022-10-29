import pytest

from utils.common import rewrite


@pytest.mark.SMOKE
@pytest.mark.DAILY
@rewrite()
def test_demo_01():
  """演示用例"""
  pass