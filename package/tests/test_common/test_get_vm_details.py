from unittest import TestCase
from cloudshell.cp.aws.aws_shell import AWSShell
from mock import Mock
from jsonpickle import encode
from cloudshell.cp.aws.domain.common.vm_details_provider import VmDetailsProvider


class TestGetVmDetails(TestCase):
    def setUp(self):
        self.vmDetailsProvider = VmDetailsProvider()

    def test_get_vm_details(self):
        shell = AWSShell()
        requests_json = encode({'items': [{'deployedAppJson': { 'name': 'something', 'vmdetails': {'uid': '514'}}}]})
        shell.get_vm_details(Mock(), Mock(), requests_json)

    def test_get_volume_when_empty(self):
        instance = Mock()
        instance.volumes.all = lambda: []
        volume = self.vmDetailsProvider._get_volume(instance)
        self.assertTrue(volume is None)

    def test_get_volume(self):
        volume1 = 'hi'
        instance = Mock()
        instance.volumes.all = lambda: [volume1]
        volume = self.vmDetailsProvider._get_volume(instance)
        self.assertTrue(volume==volume1)

    def test_get_volume_size(self):
        volume = Mock()
        volume.size = 10
        size = self.vmDetailsProvider._get_volume_size(volume)
        self.assertTrue(size == '10 GiB')
        volume = None
        size = self.vmDetailsProvider._get_volume_size(volume)
        self.assertTrue(size is None)

    def test_get_volume_type(self):
        volume = Mock()
        volume.volume_type = 'hi'
        volume_type = self.vmDetailsProvider._get_volume_type(volume)
        self.assertTrue(volume_type == 'hi')
        volume = None
        volume_type = self.vmDetailsProvider._get_volume_type(volume)
        self.assertTrue(volume_type is None)

    def test_get_volume_id(self):
        volume = Mock()
        volume.volume_id = 'hi'
        volume_id = self.vmDetailsProvider._get_volume_id(volume)
        self.assertTrue(volume_id == 'hi')
        volume = None
        volume_id = self.vmDetailsProvider._get_volume_id(volume)
        self.assertTrue(volume_id is None)