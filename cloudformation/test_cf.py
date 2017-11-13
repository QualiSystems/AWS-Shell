from unittest import TestCase

import json


class TestCloudFormation(TestCase):
    def setUp(self):
        pass

    def test_main_json_valid(self):
        json_file = open('0_Main.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_main_ex_json_valid(self):
        json_file = open('0_Main_EX.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_main_ex_no_vpn_json_valid(self):
        json_file = open('0_Main_EX_No_VPN.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_vpc_json_valid(self):
        json_file = open('1_VPC.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_vpc_ex_json_valid(self):
        json_file = open('1_VPC_EX.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_vpc_ex__no_vpn_json_valid(self):
        json_file = open('1_VPC_EX_No_VPN.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_ec2_json_valid(self):
        json_file = open('2_EC2.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_ec2_ex_json_valid(self):
        json_file = open('2_EC2_EX.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)

    def test_ec2_ex__no_vpn_json_valid(self):
        json_file = open('2_EC2_EX_No_VPN.json', 'r')
        json_string = json_file.read()
        json.loads(json_string)
