class AwsApiClients(object):
    def __init__(self, ec2_session, s3_session, ec2_client):
        """
        :param boto3.resources.base.ServiceResource ec2_session:
        :param boto3.resources.base.ServiceResource s3_session:
        :param EC2.Client ec2_client:
        :return:
        """
        self.ec2_session = ec2_session
        self.s3_session = s3_session
        self.ec2_client = ec2_client
