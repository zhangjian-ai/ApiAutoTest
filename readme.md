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

2. 新增 用例(可以通过build工具直接构建)

   所有用例都规划到 tests 目录下，可以根据业务模块再细分文件夹

   ```python
   # 文件名: test_demo.py
   
   import pytest
   
   from utils.common import rewrite
   
   
   @pytest.mark.DAILY                   # 1、用例mark
   @rewrite()                           # 2、这个装饰器一定要写
   def test_demo_01():
       """演示用例"""                     # 3、用例描述信息，在 测试数据还会再写一次，这里写出来只是为了方便理解
       pass                             # 4、函数体就这样 写个 pass 就行
   ```

3. 用例数据

   1. 所有测试数据都规划到 data 目录下;
   2. 模版符号均是 英文符号;
   3. 模版语法都必须放在字符串中，可以使用 多个 模版，但不支持随意嵌套使用;
   4. 同时 step 级别的参数化，仅在当前 step 有效;
   5. 如果确实需要将其他函数返回值或者关联值作为参数传递给当前step中的模版函数，则需要将传入的函数通过step级别的参数再引用一次，详见示例

   > 四个模版语法：
   >
   >
   > 1. 动态数据替换
   >
   >    ```yaml
   >    # 语法
   >    !<表达式>
   >
   >    # 示例
   >    !<Fabricate.random_text('?')>
   >
   >    # 说明
   >    1、框架会到factory模块中去找 Fabricate 类，并调用类中的 random_text 方法。这里 调用方法和在代码中一样，是可以直接传递参数的。
   >    2、Fabricate 类，在同一个用例中，相同方法相同入参，多次调用时，在当前用例返回相同数据。其他 类 也可通过配置实现该功能。
   >    ```
   >
   > 2. 关联数据替换（从该接口之前调用的接口响应中获取某个值）
   >
   >    ```yaml
   >    # 语法
   >    @<索引,jsonpath表达式>
   >       
   >    # 示例
   >    @<0,$.data[0].id>
   >       
   >    # 说明
   >    0 : 就是该用例的已经完成请求多个接口中的第一个接口响应结果中去匹配，索引值从 0 开始
   >    $.data[0].id : 这就是一个 jsonpath 表达式，用于定位到我们的目标数据
   >    ```
   >    
   > 3. 用例参数化
   >
   >    ```yaml
   >    # 语法
   >    %<参数的KEY>
   >
   >    # 示例
   >    %<ids>
   >
   >    # 说明
   >    参数化模版中的key，必须要是实现配置好的。即在param字段中，配置了这样的键。示例中就要求 用例的 param 中配置 ids。
   >    
   >    ```
   >    
   > 4. step 参数化
   >
   >    ```yaml
   >    # 语法
   >    ~<step参数的KEY>
   >
   >    # 示例
   >    ~<names>
   >
   >    # 说明
   >    参数化模版中的key，必须要是实现配置好的。即在param字段中，配置了这样的键。示例中就要求 当前step的 param 中配置 names；
   >    step 级别的模版由于作用域的关系，可以放到 其他模版 内部使用
   >    
   >    ```

   **注意：data 目录下的目录结构应该和 tests 下的目录结构完全一致，且 一个 .py 文件对应一个 .yaml 配置文件，一个 测试函数 对应到 yaml 中的一个key**

   ```yaml
   # 文件名: test_demo.yaml  (和测试文件同名，仅后缀不一样)
   
   # 演示用例
   test_demo_01:                                            # 1、和测试函数同名的 key，它的内容就是一个测试用例需要的全部信息
     spec:
       marks: [ "SMOKE","DAILY" ]
     info:                                                  # 4、用例信息
       desc: "演示用例"
       author: "xz"
       level: "p1"
       time: "2022.10.05"
     steps: [                                               # 5、测试步骤，里面一个 {} 表示一个接口
       {
         api: "baidu.home",                                 
         log: "访问主页",                            
         request: {                                         # 7、请求数据。内部的字段同标准库 requests.request 方法的入参
         },
         response: {                                        # 8、预期响应对象，仅写需要验证的key，层级结构保持和响应结果一致即可
           code: 0,
           data: { "==": 1 }                                # 9、特殊key: "<", ">", "==", ">=", "<=", "!=" 比较运算，这里表示返回值小于1
         }
       },
       {
         api: "baidu.demo",                                 # 10、这个接口仅演示部分用法，不是项目中真实的接口
         rule: {                                            # 11、调度规则，可不写。默认接口只会调用一次并验证。针对一些要查询进度的接口有用
           timeout: 0,                                      # 12、超时时间
           interval: 3                                      # 13、每次调度的时间间隔(s)
         },
         param: {
           code: "@<0,$.data.id>"                           # 15、关联数据替换模版
         },
         request: {							
           data: {														
             content: "!<Fabricate.random_text('?')>",     # 14、动态数据替换模版
             code: "!<Fabricate.random_text(~<code>)>",    # 16、模版之间不能任意嵌套，可通过step参数化的方式，将其他模版返回值传递给当前模版
             detail: {
               type: "@<0,$.data.id>" ,                    # 17、关联数据替换模版，只要不是嵌套场景，都可直接使用模版语法
               text: "!<Fabricate.random_text()>"
             }
           }
         },
         response: {
           code: 0,
           message: "success",
           status_code: 200                                # 18、当需要验证响应code的时候，像这样写到第一层级即可
         }
       }
     ]
   ```

4. 使用 build.py

   ```python
   if __name__ == '__main__':
       # yaml文件路径。相对项目根目录的路径
       yaml_path = ""
   
       # 用例名称
       case_name = ""
   
       # 是否调试，调试模式下不会构建case
       debug = 1
   
       manage(yaml_path, case_name, debug)
   ```

   

