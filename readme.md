## 简介

基于 pytest。

## 用例编写

1. 新增API

   如果编写的用到的api不存在，那么就需在在对应服务的yaml配置文件中添加

   ```yaml
   # 百度首页                                          # 1、为了后期维护，api都应该写上备注
   home:                                             # 2、api 名字，测试数据中通过这个名字引用
     url: "/"
     method: "GET"
   ```

2. 新增 用例(可以通过debug工具直接构建)

   所有用例都规划到 tests 目录下，可以根据业务模块再细分文件夹

   ```python
   # 文件名: test_demo.py
   
   import pytest
   
   from utils.common import rewrite
   
   
   @pytest.mark.daily                   # 1、用例mark
   @rewrite()                           # 2、这个装饰器一定要写
   def test_demo_01():
       """演示用例"""                     # 3、用例描述信息，在 测试数据还会再写一次，这里写出来只是为了方便理解
       pass                             # 4、函数体就这样 写个 pass 就行
   ```

3. 用例数据

   > data 目录下的目录结构应该和 tests 下的目录结构完全一致，且 一个 .py 文件对应一个 .yaml 配置文件，一个 测试函数 对应到 yaml 中的一个key

   - 所有测试数据都规划到 data 目录下
   - 模版语法都必须放在字符串中，可以使用 多个 模版，但**不能嵌套**
   - 在用例和steps中都可以增加param字段来表示参数化（使用过程见示例）
   - step 级别的参数化，参数仅在当前 step 有效
   - 参数化的key，可在模版语法中直接当做变量使用
   - r对象。框架为每个用例提供一个r对象列表，后面的接口可通过`r[i]`的方式获取前面对象的返回值
   - factory 目录，里面用来存放自定义的类和方法，以动态构造数据

   - **模版语法：**
     模版语法的作用就是为了动态的获取、关联数据而规定的一种写作格式。

     ```shell
     # 语法
     @<表达式>
     
     # 示例
     @<Fab.random_text('?')>
     
     # 说明
     1、框架会到factory模块中去找 Fab 类，并调用类中的 random_text 方法。这里 调用方法和在代码中一样，是可以直接传递参数的。
     2、在同一个模版语法内，可直接使用参数化字段作为变量使用，r对象也可直接作为变量使用，只需要遵循python语法规则即可。
     ```

   - **编写示例：**

     ```yaml
     test_demo_01:
       spec:
         marks: [ "smoke" ]  # 用例的mark
         skips: [ ]  # 跳过分支
       meta:
         desc: "演示用例"
         author: "goodman"
         level: "P1"
         time: "2022.10.26"
       steps: [
         {
           api: "httpbin.post",  # 接口api名称
           desc: "演示post接口调用", # 当前步骤的描述信息
           request: { # 请求对象和标准库http中的字段相同，这里不关心url和method
             data: {
               key: "豫章故郡，洪都新府",
               val: "萍水相逢，尽是他乡之客"
             },
             headers: {
               "Auth": "Copyright reserved, please purchase"
             }
           },
           response: { # 响应对象为接口返回的json对象。响应体中自动装配status_code；如果是文件下载接口，还会装载size和file字段
             json: {
               key: "豫章故郡，洪都新府",
               val: "萍水相逢，尽是他乡之客"
             },
             status_code: 200
           }
         }
       ]
     
     test_demo_02:
       spec:
         marks: [ "smoke" ]
       meta:
         desc: "参数化演示用例"
         author: "goodman"
         level: "P1"
         time: "2022.10.26"
       param: # 用例参数化，下面的参数将逐个分组拆成多个用例
         text: "@<Fab.many_text(prefix='参数化随机文本: ', num=4, length=4)>"
         answer: [ '其疾如风', '其徐如林', '侵掠如火', '不动如山' ]  # text 参数经转化后会有4个值，所以这里也需要四个值
     
       steps: [
         {
           api: "httpbin.post",
           desc: "参数化演示 - @<answer>",  # 描述信息中也可以使用参数化中的变量
           param: { # 步骤参数化，有几组参数则该步骤执行几轮。注意：如果步骤参数化字段和用例参数化字段同名，那么在后续使用中前者将覆盖后者
             text: [ '第一次执行: @<text>', '第二次执行: @<text>' ],
             name: [ '@<answer>', '@<Fab.to_name(answer)>' ]
           },
           request: {
             data: {
               key: "@<text>",
               val: "@<name>"
             }
           },
           response: {
             status_code: 200
           }
         }
       ]
     
     test_demo_03:
       spec:
         marks: [ "smoke" ]
         skips: [ ]
       meta:
         desc: "演示用例"
         author: "goodman"
         level: "P1"
         time: "2022.10.26"
       steps: [
         {
           api: "httpbin.post",
           desc: "演示post接口调用",
           request: {
             data: {
               key: "score",
               val: [ 99, 100, 98, 89 ]
             },
             headers: {
               "Auth": "Copyright reserved, please purchase"
             }
           },
           response: {
             json: {
               key: "score",
               val: [ 99, 100, 98, 89 ]
             },
             status_code: 200
           }
         },
         {
           api: "httpbin.post",
           desc: "演示post接口调用",
           request: {
             data: {
               score: "score",
               val: "@<r[0]['json']['val']>"  # 通过r对象加下标，来获取当前用例第0次请求的响应结果中的值
             },
             headers: {
               "Auth": "Copyright reserved, please purchase"
             }
           },
           response: {
             json: {
               score: "score",
               val: {  # 这里使用逻辑比较检验结果，如果是列表检验长度，如果是字符串数字等直接比较大小
                 ">": 2,  # 检验返回值是否大于2
                 "==": 4,  # 检验是否等于4
                 "not in": 101  # 检验返回值是否包含 101 这一项
               }
             },
             status_code: 200
           }
         }
       ]
     ```

     

4. 使用 debug.py

   ```python
   #########################################
   ############ Automation Test ############
   #########################################
   
   if __name__ == '__main__':
       from utils.common import debug
   
       # 测试用例数据文件的路径
       yaml_path = "data/demo/test_demo.yaml"
   
       # 用例名称
       case_name = "test_demo_02"
   
       # 是否调试，调试模式下不会构建case
       # 0/1
       flag = 1
   
       debug(yaml_path, case_name, flag)
   ```
   
   

