"""
@Project: bot3-env-verify
@File: entry.py
@Author: Seeker
@Date: 2023/7/10 11:44 下午
"""
from abc import abstractmethod
from _pytest.config import Config


class Entry:
    """
    入口类
    """
    config: Config = None


class Setup(Entry):
    """
    前置基类
    """

    @abstractmethod
    def before(self):
        """
        前置操作逻辑
        """
        pass

    def get_headers(self):
        """
        为http请求提供通用header信息
        优先级低，会被具体用例header覆盖相同的key
        """
        pass

    def get_host(self):
        """
        获取请求的主机地址
        """
        pass


class Teardown(Entry):
    """
    后置基类
    """

    @abstractmethod
    def after(self):
        """
        后置操作逻辑
        """
        pass
