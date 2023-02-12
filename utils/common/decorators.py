import time
import types
import pytest

from functools import wraps

from utils.common import log


def retry(count: int = 5, interval: int = 2, throw: bool = True):
    """
    失败重试
    默认重试 5 次，间隔 2 秒
    :param count:
    :param interval:
    :param throw:
    :return:
    """

    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            c = count
            i = interval
            while c > 0:
                try:
                    response = func(*args, **kwargs)
                except Exception as e:
                    c -= 1
                    if c == 0:
                        log.error(str(e))
                        if throw:
                            raise e
                        break
                    time.sleep(i)
                    continue

                return response

        return inner

    return outer


def rewrite(template=None):
    """
    动态生成测试函数
    作用在用例的执行阶段
    """
    if not template:
        template = '''def func(executor):
            executor.schedule()'''

    def create_func(func):

        # 将code串编译成code对象
        code = compile(source=template, filename=func.__name__, mode="exec").co_consts[0]
        # 创建函数
        # globals 选项为函数提供全局变量。比如函数内部需要调用其他方法，如果不指定会ERROR
        # locals()/globals() 内置函数分别返回局部(所在局部块，这里就是函数内部作用域)/全局(当前模块)的作用域字典
        function = types.FunctionType(code=code, globals=globals(), name=func.__name__)

        # 校验函数
        if not function:
            log.error(f"动态构建测试函数: {func.__name__} 失败")
            pytest.fail(msg=f"动态构建测试函数: {func.__name__} 失败", pytrace=False)

        return function

    return create_func
