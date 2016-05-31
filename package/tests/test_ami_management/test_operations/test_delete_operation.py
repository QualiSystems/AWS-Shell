from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation


class TestDeleteOperation(TestCase):
    def setUp(self):
        self.ec2_session = Mock()
        self.delete_operation = DeleteAMIOperation(Mock(), Mock(), Mock(), Mock())
        self.instance = Mock()
        self.delete_operation.ec2_api.get_instance_by_id = Mock(return_value=self.instance)

    def test_delete_operation(self):
        self.delete_operation.delete_instance(self.ec2_session, 'id')

        self.assertTrue(self.delete_operation.ec2_api.get_instance_by_id.called_with(self.ec2_session, 'id'))
        self.assertTrue(self.instance.terminate.called)
        self.assertTrue(self.delete_operation.instance_waiter.wait.called_with(self.instance,
                                                                               self.delete_operation.instance_waiter.TERMINATED))
