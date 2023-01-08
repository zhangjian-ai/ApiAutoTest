"""
@Project: bot3-env-verify
@File: execute.py
@Author: Seeker
@Date: 2022/10/26 7:16 下午
"""
import os
import json

import requests
import traceback

from urllib import parse

from utils.common import log, TEMP_DIR


def http_request(method="POST", url=None, data=None, params=None, headers=None, cookies=None, detail=True):
    """
    二次封装 http request 方法
    """
    # 日志打印
    if detail:
        log.info(f'请求地址: {url}')
        log.info(f'请求方式: {method}')
        log.info(f'请求头: {headers}')
        log.info(f'查询参数: {params}')
        log.info(f'表单参数: {data}')

    # 为POST请求处理Content-Type
    if method.upper() == "POST":
        if headers is None:
            headers = {}

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if 'json' in headers.get("Content-Type"):
            data = json.dumps(data)

    try:
        response = requests.request(method, url, data=data, params=params, headers=headers, cookies=cookies)
        res = None
        try:
            res = response.json()
        except:
            pass

        if detail:
            log.info(f'状态码: {response.status_code}')

        if res:
            if detail:
                log.info(f'响应结果: {res}')
            res["status_code"] = response.status_code
            return res

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

            # 为结果增加 content、file 字段
            # content 记录二进制长度
            res["content"] = len(response.content)
            res["file"] = file

        if detail:
            log.info(f'响应结果: {res}')

        return res

    except Exception as e:
        log.error(f'http 请求异常: {traceback.format_exc()}')
        raise e


def verify(expect: dict, response: dict):
    """
    验证 expect 中的键值是否都能在 response 中找到且一致
    """

    # 验证实际结果是否与预期一致
    for key, value in expect.items():
        # 比较运算处理
        if key in ("<", ">", "==", ">=", "<=", "!="):
            real_value = response
            if not isinstance(response, (int, float, str)):
                real_value = len(response)

            assert eval(f"{real_value} {key} {value}"), f'\n' \
                                                        f'KEY: {key} \n' \
                                                        f'运算符: {key} ' \
                                                        f'(如果实际返回值是一个对象，那么此时检验的是对象的长度) \n' \
                                                        f'预期值: {value}\n' \
                                                        f'实际值: {real_value}\n' \
                                                        f'返回值: {response}\n'

        # 包含关系
        elif key in ("in", "not in"):
            if not isinstance(response, (list, str, dict)):
                assert False, f'\n' \
                              f'KEY: {key} \n' \
                              f'运算符: {key} ' \
                              f'预期值: {value}\n' \
                              f'实际值: {response} 的类型不支持包含关系运算\n'

            elif isinstance(value, dict):
                _verify_list(key, [value], response, operate=key)

            elif isinstance(value, (list, tuple)):
                _verify_list(key, value, response, operate=key)

            else:
                assert eval(f"{value} {key} {response}"), f'\n' \
                                                          f'KEY: {key} \n' \
                                                          f'运算符: {key} ' \
                                                          f'预期值: {value}\n' \
                                                          f'实际值: {response}\n' \
                                                          f'包含关系运算结果不为真'

        # any 预期列表中任意一个值在实际响应中就算通过
        elif key in ("any",):
            # 使用 any 时，要求预期值是列表或元组
            assert isinstance(value, (list, tuple)), f'\n' \
                                                     f'KEY: {key} \n' \
                                                     f'预期值: {value} \n' \
                                                     f'使用 any 关键字时，要求预期值是列表或元组'
            success = False
            # 将预期值依次放入列表校验，直到校验成功
            for sub_val in value:
                try:
                    _verify_list(key, [sub_val], response)
                    success = True
                    break
                except AssertionError:
                    pass

            assert success, f'\n' \
                            f'KEY: {key} \n' \
                            f'预期值: {value} \n' \
                            f'预期值: {response} \n' \
                            f'预期结果中没有任何值在实际列表中存在'

        # 如果预期值是str、int、float那么就直接对比
        elif isinstance(value, (str, int, float)):
            assert isinstance(response, dict) \
                   and value == response.get(key), f'\n' \
                                                   f'KEY: {key} \n' \
                                                   f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                                   f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n'

        # 如果预期值是list则便利预期列表中的item是否都在实际结果中能找到
        elif isinstance(value, (list, tuple)):
            _verify_list(key, value, response.get(key))

        # 如果预期值是dict则再次调用本方法进行递归验证
        elif isinstance(value, dict):
            assert isinstance(response, dict), f'\n' \
                                               f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                               f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n' \
                                               f"响应对象实际类型是: {type(response)}，预期类型是 DICT\n"
            verify(value, response.get(key))


def _verify_list(key: str, expect: list, response: list, operate: str = "in"):
    """
    针对列表验证
    key 为预期列表expect在父级字典对应的键，传递过来主要为了打印日志
    operate 取值为 in、not in 用于表示包含和不包含的关系
    """
    assert isinstance(response, list), f'\n' \
                                       f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                       f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n' \
                                       f"响应对象实际类型是: {type(response)}，预期类型是 LIST\n"

    # 检查实际值的类型
    assert isinstance(response, (list, tuple)), f'\n' \
                                                f'KEY: {key} \n' \
                                                f'预期值: {expect}\n' \
                                                f'实际值: {response}\n'

    # # 列表长度校验
    # if len(value) != len(real_value):
    #     assert False, f'\n' \
    #                   f'KEY: {key} \n' \
    #                   f'预期列表长度: {len(value)}\n' \
    #                   f'实际列表长度: {len(real_value)}\n'

    # 列表项依次校验
    for sub_val in expect:
        # 此处不考虑列表项仍然是列表的情况，此种情况也不能出现在脚本中
        if isinstance(sub_val, (list, tuple)):
            assert False, f'\n' \
                          f'KEY: {key}\n' \
                          f'预期值: {expect}\n' \
                          f'结果验证中不允许列表嵌套列表的预期值'

        # 常规类型时，考虑返回值可能无序，直接用 operate 执行运算
        elif isinstance(sub_val, (str, int, float)):
            assert eval(f"{sub_val} {operate} {response}"), f'\n' \
                                                            f'KEY: {key}\n' \
                                                            f'预期列表: {expect}\n' \
                                                            f'实际列表: {response}\n' \
                                                            f'缺失表项: {sub_val}'

        # 如果列表项是字典，那么就便利实际结果列表依次对比直到通过
        elif isinstance(sub_val, dict):
            status = operate == "not in"
            for item in response:
                if not isinstance(item, dict):
                    continue
                try:
                    verify(sub_val, item)
                    status = not status
                    break
                except AssertionError:
                    pass

            assert status, f'\n' \
                           f'KEY: {key} \n' \
                           f'运算符: {operate} \n' \
                           f'预期值: {sub_val}\n' \
                           f'实际值: {response}\n' \
                           f'包含关系运算结果不为真'
