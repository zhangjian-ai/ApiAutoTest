import pytest


def pytest_cat_case_validator(request):
    """
    根据测试分支检查当前用例是否有效
    """

    data = request.param
    spec = data.get("spec", {})
    branch = request.config.getoption("branch")

    branches = spec.get("branches", [])

    if branches and branch not in branches:
        pytest.skip(f"分支<{branch}>不执行用例: {request.function.__name__}")
