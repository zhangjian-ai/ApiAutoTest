import time
import pytest

from py.xml import html

from utils.common import log

"""
设置html报告样式
依赖插件 pytest-html
整个导入到 conftest.py
"""


@pytest.mark.optionalhook
def pytest_html_report_title(report):
    report.title = "测试报告"


@pytest.mark.optionalhook
def pytest_metadata(metadata):
    pass


@pytest.mark.optionalhook
def pytest_html_results_summary(prefix):
    # 统计报告前缀
    pass


@pytest.mark.optionalhook
def pytest_html_results_table_header(cells):
    # 删除link列
    cells.pop(-1)

    # 表头
    cells.insert(3, html.th('Time', class_='sortable time', col='time'))
    cells.insert(4, html.th('用例描述'))
    cells.insert(5, html.th("作者"))
    cells.insert(6, html.th("用例等级"))
    cells.insert(7, html.th("更新时间"))


@pytest.mark.optionalhook
def pytest_html_results_table_row(report, cells):
    # 删除link列
    cells.pop(-1)

    if report:
        try:

            # 测试时长
            cells.insert(2, html.td(html.span(cells.pop(2).pop(), style_="color: black")))

            # 自定义列
            properties = dict(report.user_properties)
            cells.insert(3, html.td(html.p(time.strftime('%m-%d %H:%M:%S'), class_='col-time')))

            # Test列处理
            # 用例名称，处理报告中文乱码，skipped用例不做处理
            old = cells.pop(1).pop()
            text = properties.get("origin") + "::" + old.split("::")[1]
            if "Skipped" not in cells[0]:
                text = text.encode("raw_unicode_escape").decode("utf-8")

            cells.insert(1, html.td(html.span(text, style_="color: saddlebrown")))

            # 用例说明
            desc_td = html.td()
            desc_td.insert(0, html.p(properties.get('desc', ""),
                                     style_="font-weight: 400; color: black; margin: 0"))

            if properties.get('params'):
                for key, val in properties.get('params').items():
                    div = html.div()
                    div.append(html.span(f"| {key} : ", style_="color: green"))
                    div.append(html.span(val, style_="color: peru"))

                    desc_td.append(div)

            cells.insert(4, desc_td)

            # 其他信息
            cells.insert(5, html.td(html.span(properties.get('author', ""), style_="color: black")))
            cells.insert(6, html.td(html.span(properties.get('level', ""), style_="color: black")))
            cells.insert(7, html.td(html.span(properties.get('time', ""), style_="color: black")))

        except Exception as e:
            log.error(str(e))


@pytest.mark.optionalhook
def pytest_html_results_table_html(report, data):
    # 通过的用例不记录日志
    if report.passed:
        data.clear()
        data.append(html.div("we will not record log for passed case.", class_="empty log"))
