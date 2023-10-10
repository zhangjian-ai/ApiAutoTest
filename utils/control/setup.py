"""
@Project: api-auto-test
@File: control.py
@Author: Seeker
@Date: 2023/7/9 12:34 下午
"""
from utils.framework.open.entry import Setup


class MySetup(Setup):
    """
    自定义前置类
    """

    def before(self):
        for product in self.im.get("products").keys():
            if product == "httpbin":
                p = self.im.get(product)
                for api in p.apis.values():
                    api["url"] = f"{self.config.getoption('host')}:{self.config.getoption('port')}{api['url']}"







