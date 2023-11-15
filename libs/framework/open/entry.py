from abc import abstractmethod
from _pytest.config import Config

from config.settings import CUSTOM_UTILS
from libs.framework.inner.db import MysqlConnPool
from libs.framework.inner.loads import load_yours
from libs.framework.inner.support import InterfaceManager


class Entry:
    """
    纯纯基类
    """
    source: dict = None
    config: Config = None
    im: InterfaceManager = None
    mysql_pool: MysqlConnPool = None

    @classmethod
    def assemble(cls, config: Config):
        cls.config = config

        # 接口管理实例
        cls.im = InterfaceManager()

        # 收集所有的工具类及方法，放到一个字典中
        # 同时注入 fixture 到 conftest
        cls.source = load_yours(CUSTOM_UTILS)

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
