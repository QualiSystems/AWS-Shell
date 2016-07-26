from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.domain.services.s3.bucket import S3BucketService
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel


class GetAccessKeyOperation(object):
    def __init__(self, key_pair_service):
        """
        :param KeyPairService key_pair_service:
        :param S3BucketService s3_service:
        :return:
        """
        self.key_pair_service = key_pair_service

    def get_access_key(self, s3_session, aws_ec2_resource_model, reservation_id):
        """
        Returns the content of the pem file stores in s3 for the given reservation
        :param s3_session:
        :param AWSEc2CloudProviderResourceModel aws_ec2_resource_model: The resource model of the AMI deployment option
        :param str reservation_id:
        :return:
        """
        return self.key_pair_service.load_key_pair_by_name(s3_session=s3_session,
                                                           bucket_name=aws_ec2_resource_model.key_pairs_location,
                                                           reservation_id=reservation_id)
