from unittest import TestCase

from botocore.exceptions import ClientError
from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation


class TestDeleteOperation(TestCase):
    def setUp(self):
        self.ec2_session = Mock()
        self.tag_service = Mock()
        self.security_group_service = Mock()
        self.delete_operation = DeleteAMIOperation(Mock(), Mock(), self.security_group_service, self.tag_service)
        self.instance = Mock()
        self.logger = Mock()
        self.delete_operation.instance_service.get_instance_by_id = Mock(return_value=self.instance)

    def test_delete_operation(self):
        self.instance.security_groups = MagicMock()

        self.delete_operation.delete_instance(self.logger, self.ec2_session, 'id')

        self.delete_operation.instance_service.get_instance_by_id.called_with(self.ec2_session, 'id')
        self.delete_operation.instance_service.terminate_instance.assert_called_with(self.instance)

    def test_delete_operation_with_exclusive_security_group(self):
        # arrange
        sg_desc = {'GroupId': 'sg_id'}
        self.instance.security_groups = [sg_desc]
        sg = Mock()
        self.ec2_session.SecurityGroup = Mock(return_value=sg)
        self.tag_service.find_isolation_tag_value = Mock(return_value='Exclusive')

        # act
        self.delete_operation.delete_instance(self.logger, self.ec2_session, 'id')

        # assert
        self.assertTrue(self.tag_service.find_isolation_tag_value.called)
        self.security_group_service.delete_security_group.assert_called_with(sg)

    def test_delete_operation_instance_not_exist(self):
        self.instance.security_groups = MagicMock()

        error_response = {'Error': {
            'Code': 'InvalidInstanceID.NotFound'
        }}
        self.delete_operation.instance_service.get_instance_by_id = Mock(side_effect=ClientError(error_response, 'Test'))

        # act
        self.delete_operation.delete_instance(self.logger, self.ec2_session, 'id')

        # assert
        self.logger.info.assert_called_with("Aws instance id was already terminated")
        assert not self.delete_operation.instance_service.terminate_instance.called
