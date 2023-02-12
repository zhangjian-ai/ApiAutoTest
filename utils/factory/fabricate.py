import random

from faker import Faker
from string import ascii_letters, digits


class Fab:
    """
    Fabricate
    虚构数据类
    """

    faker = Faker(locale='zh_CN')

    @staticmethod
    def random_str(n: int = 10):
        """
        返回一个随机字符串，默认10位
        :param n:
        :return:
        """
        string = ascii_letters + digits

        return "".join(random.sample(string, n))

    @classmethod
    def random_text(cls, suffix="", num=12):
        """
        随机文本
        :return:
        """
        text = cls.faker.sentence(nb_words=num, variable_nb_words=False)

        return text[:num] + suffix

    @classmethod
    def many_text(cls, prefix="", num=3, length=8):
        """
        生成指定数量的随机文本
        num 表示返回文本的个数
        length 表示文本的长度
        :return: list 对象
        """
        texts = []
        for i in range(num):
            text = cls.random_text(num=length)
            if prefix:
                text = prefix + text
            texts.append(text)

        return texts

    @classmethod
    def to_name(cls, title):
        """
        根据称号返回名字
        """
        if title == "其疾如风":
            return "钟离昧"
        elif title == "其徐如林":
            return "季布"
        elif title == "侵掠如火":
            return "龙且"
        elif title == "不动如山":
            return "英布"

        return "路人甲"
