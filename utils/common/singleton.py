import threading
from collections import defaultdict


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
