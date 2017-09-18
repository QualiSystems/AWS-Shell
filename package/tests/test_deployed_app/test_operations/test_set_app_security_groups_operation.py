from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.deployed_app.operations.set_app_security_groups import SetAppSecurityGroupsOperation


class TestSetAppSecurityGroupsOperation(TestCase):
    def setUp(self):
        self.instance_service = Mock()
        self.tag_service = Mock()
        self.security_group_service = Mock()
        self.operation = SetAppSecurityGroupsOperation(instance_service=self.instance_service,
                                                       tag_service=self.tag_service,
                                                       security_group_service=self.security_group_service)

    def test_set_apps_security_groups(self):
        pass
