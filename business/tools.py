from faker import Faker

"""
定义业务相关工具类啥的
"""


class DataFox:
    """
    数据伪造
    """

    faker = Faker(locale='zh_CN')

    @classmethod
    def random_text(cls, suffix="", num=12):
        """
        随机文本
        :return:
        """
        text = cls.faker.sentence(nb_words=num, variable_nb_words=False)

        return text[:num] + suffix
