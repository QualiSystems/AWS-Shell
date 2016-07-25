from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.ami_management.operations.access_key_operation import GetAccessKeyOperation


class TestAccessKeyOperation(TestCase):
    def setUp(self):
        self.key_pair_service = Mock()
        self.operation = GetAccessKeyOperation(key_pair_service=self.key_pair_service)

    def test_get_access_key(self):
        s3_session = Mock()
        aws_ec2_resource_model = Mock()
        aws_ec2_resource_model.key_pairs_location = 'bucket'
        reservation_id = 'reservation_id'

        pem_file_content = 'bla bla bla'
        self.key_pair_service.load_key_pair_by_name = Mock(return_value=pem_file_content)

        key_data = self.operation.get_access_key(s3_session=s3_session,
                                                 aws_ec2_resource_model=aws_ec2_resource_model,
                                                 reservation_id=reservation_id)

        self.assertEquals(key_data, pem_file_content)
        self.key_pair_service.load_key_pair_by_name.assert_called_with(s3_session=s3_session,
                                                                       bucket_name=aws_ec2_resource_model.key_pairs_location,
                                                                       reservation_id=reservation_id)
