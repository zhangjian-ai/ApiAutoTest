import inspect
import json
import os
import tkinter as tk
from _tkinter import TclError
from tkinter import ttk

from config import CONF_FILE, BASE_DIR, CUSTOM_LIBS, CASE_DIR
from framework.core.loads import load_yaml, load_interface, scan_custom, load_case

settings = load_yaml(CONF_FILE)["nightingale"]

class Seeker:
    """
    Seeker 助手
    """

    def __init__(self):
        # 创建主窗口
        window = tk.Tk()
        window.title("Seeker助手")  # 标题
        window.geometry("1300x500+100+120")  # 窗口尺寸及初始位置 (宽度x高度)+(x轴+y轴)

        # 初始按钮
        btn1 = tk.Button(window, {"text": "系统接口", "height": 2, "width": 5,
                                  "command": lambda: self.create_first(self.get_api())})
        btn2 = tk.Button(window, {"text": "可用工具", "height": 2, "width": 5,
                                  "command": lambda: self.create_first(self.get_utils())})
        btn3 = tk.Button(window, {"text": "现有用例", "height": 2, "width": 5,
                                  "command": lambda: self.create_first(self.get_cases())})

        btn1.grid(row=0, column=0)
        btn2.grid(row=1, column=0)
        btn3.grid(row=2, column=0)

        self.window = window
        self.btn1 = btn1
        self.btn2 = btn2

        self.apis = dict()
        self.utils = dict()
        self.items = dict()

        self.first_box = None
        self.second_box = None
        self.second_values = None
        self.third_values = None

        window.mainloop()

    def get_api(self):
        if not self.apis:
            for conf in settings["meta"]["products"]:
                self.apis[conf["product"]] = load_interface(os.path.join(BASE_DIR, conf["path"]))

        return self.apis

    def get_utils(self):
        if not self.utils:
            users = scan_custom(CUSTOM_LIBS)
            self.utils["user_utils"] = {}
            self.utils["fixtures"] = users[1]

            for name, unknown in users[0].items():
                source_path = inspect.getsourcefile(unknown)
                # 此处收集用户定义的类和方法
                if source_path.startswith(os.path.join(BASE_DIR, CUSTOM_LIBS)):
                    self.utils["user_utils"][name] = unknown

            system = scan_custom(os.path.join("config", "framework", "open"))
            self.utils["system_utils"] = {}
            for name, unknown in system[0].items():
                source_path = inspect.getsourcefile(unknown)
                # 框架提供的
                if source_path.startswith(os.path.join(BASE_DIR, "config", "framework", "open")):
                    self.utils["system_utils"][name] = unknown

        return self.utils

    def get_cases(self):
        if not self.items:
            # 查询出主要目录
            _, dirs, _ = os.walk(os.path.join(CASE_DIR)).__next__()

            for target in dirs:
                if not target.startswith("_"):
                    self.items[target] = load_case(os.path.join(CASE_DIR, target), "")

        return self.items

    def create_first(self, target):
        if self.first_box:
            self.first_box.destroy()

        self.second_values = target

        # 下拉框
        box = ttk.Combobox(self.window,
                           height=24,  # 高度,下拉显示的条目数量
                           width=20,  # 宽度
                           state='',  # 设置状态 normal(可选可输入)、readonly(只可选)、 disabled(禁止输入选择)
                           cursor='arrow',  # 鼠标移动时样式 arrow, circle, cross, plus...
                           font=('', 14),  # 字体
                           values=sorted(self.second_values.keys()),  # 设置下拉框的选项
                           )
        box.bind("<<ComboboxSelected>>", self.create_second)
        box.grid(row=0, column=1, padx=8)

        try:
            box.current(0)  # 默认选中第一个
            self.first_box = box
            self.create_second()
        except TclError:
            pass

    def create_second(self, *args):
        if self.second_box:
            self.second_box.destroy()

        # 上一级的值
        self.third_values = self.second_values.get(self.first_box.get())

        # 下拉框
        box = ttk.Combobox(self.window,
                           height=24,
                           width=26,
                           state='',
                           cursor='arrow',
                           font=('', 14),
                           values=sorted(self.third_values.keys()),
                           )
        box.bind("<<ComboboxSelected>>", self.create_text)
        box.grid(row=0, column=2, padx=8)

        try:
            box.current(0)  # 默认选中第一个
            self.second_box = box
            self.create_text()
        except TclError:
            pass

    def create_text(self, *args):
        # 上一级的值
        unknown = self.third_values.get(self.second_box.get())

        # 下拉框
        # ttk.
        web_text = tk.Text(self.window,
                           height=32,
                           width=85,
                           font=('', 12),
                           background="whitesmoke",
                           highlightbackground="lightseagreen"
                           )
        web_text.grid(row=0, column=5, padx=15, rowspan=100)

        content = "你在干什么~"
        if unknown:
            if isinstance(unknown, dict):
                content = json.dumps(unknown, indent=2, ensure_ascii=False)
            else:
                content = inspect.getsource(unknown)

        web_text.insert(tk.INSERT, content)
