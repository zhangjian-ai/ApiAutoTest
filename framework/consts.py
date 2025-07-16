import threading

from abc import abstractmethod
from collections import defaultdict

from _pytest.config import Config


class Singleton(type):
    """
    单例元类
    """
    __lock = threading.Lock()
    __instances = defaultdict()

    def __call__(cls, *args, **kwargs):
        # 根据调用方、调用参数生成一个唯一的key
        key = cls.__name__ + str(args) + str(kwargs)

        # 加锁，判断当前key是否已有实例
        with Singleton.__lock:
            if key not in Singleton.__instances:
                Singleton.__instances[key] = super(Singleton, cls).__call__(*args, **kwargs)

        return Singleton.__instances[key]


class HTTP:
    __slots__ = ["interface", "url", "method", "data", "params", "headers", "cookies", "verify", "stream"]

    def __init__(self, url, method="POST", data: dict = None, params: dict = None, headers: dict = None,
                 cookies: dict = None, verify=False, stream=False):
        self.interface = {}
        self.interface["url"] = self.url = url
        self.interface["method"] = self.method = method
        self.interface["data"] = self.data = data
        self.interface["params"] = self.params = params
        self.interface["headers"] = self.headers = headers
        self.interface["cookies"] = self.cookies = cookies
        self.interface["verify"] = self.verify = verify
        self.interface["stream"] = self.stream = stream


class HTPB(HTTP):
    __slots__ = ["interface", "url", "req", "resp", "gzip", "encrypt_type", "encrypt_key", "method",
                 "data", "params", "headers", "cookies", "verify", "stream"]

    def __init__(self, url, req, resp, gzip=True, encrypt_type="xor", encrypt_key="", method="POST",
                 data: dict = None, params: dict = None, headers: dict = None, cookies: dict = None, verify=False,
                 stream=False):
        super().__init__(url, method, data, params, headers, cookies, verify, stream)

        self.interface["req"] = self.req = req
        self.interface["resp"] = self.resp = resp
        self.interface["gzip"] = self.gzip = gzip
        self.interface["encrypt_type"] = self.encrypt_type = encrypt_type
        self.interface["encrypt_key"] = self.encrypt_key = encrypt_key


class Gather:
    """
    纯纯基类
    """
    utils: dict = None
    fixtures: dict = None

    config: Config = None

    @classmethod
    def assemble(cls, config: Config):
        cls.config = config

        from business import fixtures
        from business import tools

        cls.fixtures = {k: v for k, v in vars(fixtures).items() if not k.startswith("_")}
        cls.utils = {k: v for k, v in vars(tools).items() if not k.startswith("_")}


class Setup(Gather):
    @abstractmethod
    def before(self):
        """
        前置操作逻辑
        """


class Teardown(Gather):
    @abstractmethod
    def after(self):
        """
        后置操作逻辑
        """
