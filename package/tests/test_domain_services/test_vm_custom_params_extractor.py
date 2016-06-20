from unittest import TestCase

import jsonpickle
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.services.parsers.custom_param_extractor import VmCustomParamsExtractor


class TestVmCustomParamsExtractor(TestCase):
    def setUp(self):
        pass

    def test_extracor(self):
        json_str = '{"vmCustomParams":[{"name": "param", "value": "some_value"}]}'
        dict = jsonpickle.decode(json_str)
        vmdetails = DeployDataHolder(dict)

        extracotr = VmCustomParamsExtractor()
        param_value = extracotr.get_custom_param_value(vmdetails.vmCustomParams, "param")

        self.assertEqual(param_value, "some_value")


