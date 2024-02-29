from abc import abstractmethod
from _pytest.config import Config

from config import CUSTOM_LIBS
from framework.core.db import MysqlConnPool
from framework.core.loads import scan_custom
from framework.core.support import InterfaceManager


class Entry:
    """
    纯纯基类
    """
    source: dict = None
    fixtures: dict = None
    controllers: dict = None
    config: Config = None
    im: InterfaceManager = None
    mysql_pool: MysqlConnPool = None

    @classmethod
    def assemble(cls, config: Config, settings: dict):
        cls.config = config

        # 接口管理实例
        cls.im = InterfaceManager(settings.get("meta").get("products"))

        # 收集所有的工具类及方法
        cls.source, cls.fixtures, cls.controllers = scan_custom(CUSTOM_LIBS)

        # mysql 连接池
        # cls.mysql_pool = MysqlConnPool(host=config.getoption("db_host"), port=config.getoption("db_port"),
        #                                user=config.getoption("db_user"), password=config.getoption("db_pwd"))

    @classmethod
    def close(cls):
        if cls.mysql_pool:
            cls.mysql_pool.close()


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
    # 后置类标识
    __teardown__ = "session"

    @abstractmethod
    def after(self):
        """
        后置操作逻辑
        """
        pass
