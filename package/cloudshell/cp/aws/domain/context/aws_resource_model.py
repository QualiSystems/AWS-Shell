from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser


class AwsResourceModelContext(object):
    def __init__(self, context):
        """
        Initializes an instance of AwsResourceModelContext
        :param context: Command context
        :type: context: ResourceCommandContext
        """
        self.context = context
        self.model_parser = AWSModelsParser()

    def __enter__(self):
        """
        Initializes AWSEc2CloudProviderResourceModel instance from a context
        :rtype: AWSEc2CloudProviderResourceModel
        :return :
        """
        return self.model_parser.convert_to_aws_resource_model(self.context.resource)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called upon end of the context. Does nothing
        :param exc_type: Exception type
        :param exc_val: Exception value
        :param exc_tb: Exception traceback
        :return:
        """
        pass
