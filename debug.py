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
