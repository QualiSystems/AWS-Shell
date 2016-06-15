from unittest import TestCase

import jsonpickle
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder

from cloudshell.cp.aws.domain.deployed_app.operations.app_ports_operation import DeployedAppPortsOperation
from cloudshell.cp.aws.domain.services.model_parser.custom_param_extractor import VmCustomParamsExtractor


class TestDeployedAppPortsOperation(TestCase):
    def setUp(self):
        self.operation = DeployedAppPortsOperation(VmCustomParamsExtractor())

    def test_format_single_inbound(self):
        json_str = '{"vmCustomParams":[{"name": "inbound_ports", "value": "80"}]}'
        dict = jsonpickle.decode(json_str)
        vmdetails = DeployDataHolder(dict)

        result = self.operation.get_formated_deployed_app_ports(vmdetails.vmCustomParams)

        self.assertEqual(result, 'Inbound ports:\nPort 80 tcp')

    def test_format_complex_inbound(self):
        json_str = '{"vmCustomParams":[{"name": "inbound_ports", "value": "80; 1200-2300:udp; 26:tcp"}]}'
        dict = jsonpickle.decode(json_str)
        vmdetails = DeployDataHolder(dict)

        result = self.operation.get_formated_deployed_app_ports(vmdetails.vmCustomParams)

        self.assertEqual(result, 'Inbound ports:\nPort 80 tcp\nPorts 1200-2300 udp\nPort 26 tcp')

    def test_format_single_outbound(self):
        json_str = '{"vmCustomParams":[{"name": "outbound_ports", "value": "80"}]}'
        dict = jsonpickle.decode(json_str)
        vmdetails = DeployDataHolder(dict)

        result = self.operation.get_formated_deployed_app_ports(vmdetails.vmCustomParams)

        self.assertEqual(result, 'Outbound ports:\nPort 80 tcp')

    def test_format_complex_outbound(self):
        json_str = '{"vmCustomParams":[{"name": "Outbound_ports", "value": "80; 1200-2300:udp; 26:tcp"}]}'
        dict = jsonpickle.decode(json_str)
        vmdetails = DeployDataHolder(dict)

        result = self.operation.get_formated_deployed_app_ports(vmdetails.vmCustomParams)

        self.assertEqual(result, 'Outbound ports:\nPort 80 tcp\nPorts 1200-2300 udp\nPort 26 tcp')

    def test_format_complex_inbound_and_outbound(self):
        json_str = '{"vmCustomParams":[' \
                   '{"name": "inbound_ports", "value": "80; 1200-2300:udp; 26:tcp"},' \
                   '{"name": "Outbound_ports", "value": "1433; 3000-3010:udp; 30:tcp; 26:udp"}]}'
        dict = jsonpickle.decode(json_str)
        vmdetails = DeployDataHolder(dict)

        result = self.operation.get_formated_deployed_app_ports(vmdetails.vmCustomParams)

        self.assertEqual(result,
                         'Inbound ports:\nPort 80 tcp\nPorts 1200-2300 udp\nPort 26 tcp\n\n'
                         'Outbound ports:\nPort 1433 tcp\nPorts 3000-3010 udp\nPort 30 tcp\nPort 26 udp')


