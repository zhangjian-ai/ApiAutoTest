import os
import time
import json
import requests
import traceback

from urllib import parse
from functools import wraps
from google.protobuf import json_format
from grpc._channel import _MultiThreadedRendezvous

from libs.settings import TEMP_DIR
from libs.framework.open.entry import Entry
from libs.framework.open.logger import log


class DbUtils:
    """
    数据库操作 工具类
    """

    @staticmethod
    def query(sql: str = None):
        """
        装饰器
        执行查询时使用，为自定义函数注入查询结果 List[Dict]

        自定义函数形式通常应为：
            @DbUtils.query("select * from ...")
            def func(result: list[dict], params: list, size: int): ...

        @param sql:
        @return:
        """

        def outer(func):
            @wraps(func)
            def inner(*args, **kwargs):
                # 获取参数
                params = kwargs.get("params", None)
                size = kwargs.get("size", 10)

                if params and not isinstance(params, (tuple, list)):
                    raise RuntimeError(f"params 参数类型错误, 当前类型 {type(params)}, 可接受的类型有 tuple list")

                kwargs["result"] = Entry.mysql_pool.query(sql, params, size)

                return func(*args, **kwargs)

            return inner

        return outer

    @staticmethod
    def modify(sql: str = None):
        """
        装饰器
        执行增删改时使用，为自定义函数注入查询结果 int

        自定义函数形式通常应为：
            @DbUtils.query("insert into ...")
            def func(result: list[dict], params: list[list]): ...

        @param sql:
        @return:
        """

        def outer(func):
            @wraps(func)
            def inner(*args, **kwargs):
                # 获取参数
                params = kwargs.get("params", None)

                if params and isinstance(params, (tuple, list)):
                    raise RuntimeError(f"params 参数类型错误, 当前类型 {type(params)}, 可接受的类型有 tuple list")

                kwargs["result"] = Entry.mysql_pool.modify(sql, params)

                return func(*args, **kwargs)

            return inner

        return outer


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


def http_request(method="POST", url=None, data=None, params=None, headers=None, cookies=None, detail=True) -> dict:
    """
    二次封装 http request 方法
    """

    # 为POST请求处理Content-Type
    if method.upper() == "POST":
        if headers is None:
            headers = {}

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

    # 日志打印
    if detail:
        log.info(f'请求地址: {url}')
        log.info(f'请求方式: {method}')
        log.info(f'请求头: {headers}')
        log.info(f'查询参数: {params}')
        log.info(f'表单参数: {data}')

    # 处理data数据
    if data and method.upper() == "POST" and 'json' in headers.get("Content-Type"):
        data = json.dumps(data)

    try:
        response = requests.request(method, url, data=data, params=params, headers=headers, cookies=cookies)
        res = None
        try:
            res = response.json()
        except Exception as e:
            if "Content-Disposition" not in response.headers:
                log.error(f"响应结果解析异常: {str(e)}")
                log.error(f"响应文本: {response.text}")

        if detail:
            log.info(f'状态码: {response.status_code}')

        if res:
            res["status_code"] = response.status_code

        else:
            # response.json() 解析异常时，单独构建响应结果
            res = {"status_code": response.status_code}

        # 检查是否是文件下载接口
        if "Content-Disposition" in response.headers:
            # 持久化文件到本地，文件名加上一个随机串避免多用例冲突
            disposition = parse.unquote(response.headers["Content-Disposition"])
            name = disposition.rsplit('=', 1)[1].split(';', 1)[0]
            file = os.path.join(TEMP_DIR, name)

            with open(file, "wb") as f:
                f.write(response.content)

            # 为结果增加 size、file 字段
            # size 记录二进制长度
            # file 记录保存到临时目录的下载文件绝对路径
            res["size"] = len(response.content)
            res["file"] = file

        if detail:
            log.info(f'响应结果: {res}')

        return res

    except Exception as e:
        log.error(f'http 请求异常: {traceback.format_exc()}')
        raise e


def protobuf_to_dict(protobuf) -> dict:
    """
    pb转字典
    :param protobuf: pb 对象
    :return:
    """
    # 流式接口自动封装一层
    if isinstance(protobuf, _MultiThreadedRendezvous):
        res = {"stream": []}

        while True:
            try:
                res["stream"].append(protobuf_to_dict(protobuf.next()))
            except StopIteration:
                break

        return res

    string = json_format.MessageToJson(protobuf,
                                       including_default_value_fields=True,
                                       preserving_proto_field_name=True)

    return json.loads(string)
