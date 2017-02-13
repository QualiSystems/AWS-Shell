import os
from unittest import TestCase

import json


class TestAWSShell(TestCase):
    def setUp(self):
        pass

    def test_temp(self):
        def list_files_to_res(path):
            result = '\n'
            files_list = os.listdir(path)
            for f in files_list:
                result += path + f + "\n"
            return result

        res = '\n'
        res += list_files_to_res('../')
        res += list_files_to_res('../../')
        res += list_files_to_res('../../cloudformation/')

        raise Exception(res)



    def test_main_json_valid(self):
        json_file = open('../../cloudformation/0_Main.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_main_ex_json_valid(self):
        json_file = open('../../cloudformation/0_Main_EX.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_vpc_json_valid(self):
        json_file = open('../../cloudformation/1_VPC.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_vpc_ex_json_valid(self):
        json_file = open('../../cloudformation/1_VPC_EX.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_ec2_json_valid(self):
        json_file = open('../../cloudformation/2_EC2.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_ec2_ex_json_valid(self):
        json_file = open('../../cloudformation/2_EC2_EX.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)
