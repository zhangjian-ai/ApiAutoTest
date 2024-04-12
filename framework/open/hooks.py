from _pytest.fixtures import SubRequest


def pytest_cat_case_validator(request: SubRequest):
    """
    用例校验勾子
    在每个用例执行前调用
    """