"""
@Project: bot3-env-verify
@File: entry.py
@Author: Seeker
@Date: 2023/7/10 11:44 下午
"""
from abc import abstractmethod
from _pytest.config import Config

from config.settings import DATA_FACTORY
from utils.framework.inner.loads import load_module_attrs
from utils.framework.inner.support import InterfaceManager


class Entry:
    """
    核心基类
    """
    source: dict = None
    config: Config = None
    im: InterfaceManager = None

    @classmethod
    def assemble(cls, config: Config):
        cls.config = config
        cls.im = InterfaceManager()
        cls.source = load_module_attrs(DATA_FACTORY)


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
