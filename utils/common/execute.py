import json

import requests
import traceback

from utils.common import log


def http_request(method="POST", url=None, data=None, params=None, headers=None, cookies=None, detail=True):
    """
    二次封装 http request 方法
    """
    # 日志打印
    if detail:
        log.info(f'请求地址: {url}')
        log.info(f'请求方式: {method}')
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
                log.info(f'响应体: {res}')
            res["status_code"] = response.status_code
            return res

        if detail:
            log.warning(f'响应体: {response.text}')
        return {"status_code": response.status_code}

    except Exception as e:
        log.error(f'http 请求异常: {traceback.format_exc()}')
        raise e


def verify(expect: dict, response: dict):
    """
    验证 expect 中的键值是否都能在 response 中找到且一致
    """

    # 验证实际结果是否与预期一致
    for key, value in expect.items():

        # 如果预期值是str、int、float那么就直接对比
        if isinstance(value, (str, int, float)):
            # 特殊值处理，判断对象的长度
            if key == "EQUAL":
                assert value == len(response), f'\n' \
                                               f'KEY: {key} \n' \
                                               f'预期对象长度: {value}\n' \
                                               f'实际对象长度: {len(response)}\n' \
                                               f'实际对象: {response}\n'
            elif key == "GREATER":
                assert value < len(response), f'\n' \
                                              f'KEY: {key} \n' \
                                              f'预期最小长度: {int(value) + 1}\n' \
                                              f'实际对象长度: {len(response)}\n' \
                                              f'实际对象: {response}\n'
            elif key == "LESS":
                assert value > len(response), f'\n' \
                                              f'KEY: {key} \n' \
                                              f'预期最大长度: {int(value) - 1}\n' \
                                              f'实际对象长度: {len(response)}\n' \
                                              f'实际对象: {response}\n'
            else:
                assert isinstance(response, dict) \
                       and value == response.get(key), f'\n' \
                                                       f'KEY: {key} \n' \
                                                       f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                                       f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n'

        # 如果预期值是list则便利预期列表中的item是否都在实际结果中能找到
        elif isinstance(value, (list, tuple)):
            assert isinstance(response, dict), f'\n' \
                                               f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                               f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n' \
                                               f"响应对象实际类型是: {type(response)}，预期类型是 DICT\n"

            real_value = response.get(key)

            # 检查实际值的类型
            assert isinstance(real_value, (list, tuple)), f'\n' \
                                                          f'KEY: {key} \n' \
                                                          f'预期值: {value}\n' \
                                                          f'实际值: {real_value}\n'

            # 列表长度校验
            if len(value) != len(real_value):
                assert False, f'\n' \
                              f'KEY: {key} \n' \
                              f'预期列表长度: {len(value)}\n' \
                              f'实际列表长度: {len(real_value)}\n'

            # 列表项依次校验
            for index, sub_value in enumerate(value):
                # 此处不考虑列表项仍然是列表的情况，此种情况也不能出现在脚本中
                # 常规类型时，考虑返回值可能无序，因此这里用 in 断言
                if isinstance(sub_value, (str, int, float)):
                    assert sub_value in real_value, f'\n' \
                                                    f'KEY: {key}\n' \
                                                    f'预期列表: {value}\n' \
                                                    f'实际列表: {real_value}\n' \
                                                    f'缺失表项: {sub_value}'

                # 如果列表项是字典，那么要求需要校验的列表项要和实际响应列表项按索引对应
                elif isinstance(sub_value, dict):
                    # 判断返回值列表该索引处是否也为字典，如果是则 递归调用 本方法
                    if isinstance(real_value[index], dict):
                        verify(sub_value, real_value[index])
                        continue
                    assert False, f'\n' \
                                  f'KEY: {key}\n' \
                                  f'索引值: {index}\n' \
                                  f'预期列表该索引处的值: {sub_value}\n' \
                                  f'实际列表该索引处的值: {real_value[index]}'

        # 如果预期值是dict则再次调用本方法进行递归验证
        elif isinstance(value, dict):
            assert isinstance(response, dict), f'\n' \
                                               f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                               f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n' \
                                               f"响应对象实际类型是: {type(response)}，预期类型是 DICT\n"
            verify(value, response.get(key))
