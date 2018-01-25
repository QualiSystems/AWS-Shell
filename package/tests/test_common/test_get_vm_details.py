from unittest import TestCase
from cloudshell.cp.aws.aws_shell import AWSShell
from mock import Mock, MagicMock, call
from jsonpickle import encode


class TestGetVmDetails(TestCase):
    def test_get_vm_details(self):
        shell = AWSShell()

        requests_json = encode({'items': [{'deployedAppJson': { 'name': 'something', 'vmdetails': {'uid': '514'}}}]})

        #
        # requests_json = """{ 'Items': [{ 'DeployedAppJson': {
        #                             'Vmdetails': { 'Uid': '514' }
        #     }]
        #      }
        # """


        shell.get_vm_details(Mock(), Mock(), requests_json)