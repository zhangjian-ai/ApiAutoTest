from abc import abstractmethod
from _pytest.config import Config

from framework import USER_UTILS
from framework.open import hooks
from framework.core.db import MysqlPool
from framework.core.loads import scan_custom
from framework.core.assistant import InterfaceManager


class Entry:
    """
    纯纯基类
    """
    utils: dict = None
    hooks: dict = None
    fixtures: dict = None
    controllers: dict = None

    mp: MysqlPool = None
    config: Config = None
    im: InterfaceManager = None

    @classmethod
    def assemble(cls, config: Config, products: list):
        cls.config = config

        # 接口管理实例
        cls.im = InterfaceManager(products)

        # 收集所有自定义的 工具类和方法、勾子、夹具、前后置类
        cls.utils, used_hooks, cls.fixtures, cls.controllers = scan_custom(USER_UTILS)

        # 处理勾子
        cls.hooks = vars(hooks)
        cls.hooks.update(used_hooks)

    @classmethod
    def close(cls):
        if cls.mp:
            cls.mp.close()


class Setup(Entry):
    """
    前置基类
    """
    # 前置类标识
    __setup__ = "session"

    @abstractmethod
    def before(self):
        """
        前置操作逻辑
        """

    def get_headers(self):
        """
        为http请求提供通用header信息
        优先级低，会被具体用例header覆盖相同的key
        """

    def get_host(self):
        """
        获取请求的主机地址
        """


class Teardown(Entry):
    """
    后置基类
    """
    # 后置类标识
    __teardown__ = "session"

    @abstractmethod
    def after(self):
        """
        后置操作逻辑
        """
