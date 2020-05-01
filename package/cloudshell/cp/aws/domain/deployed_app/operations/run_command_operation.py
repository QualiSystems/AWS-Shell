import json

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.cm.customscript.customscript_shell import CustomScriptShell

from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.models.aws_api import AwsApiClients
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel

USER_ATTR = 'User'
PASSWORD_ATTR = 'Password'
PUBLIC_IP_ATTR = 'Public IP'


class RunCommandOperation(object):
    def __init__(self, key_pair_service):
        """
        :param KeyPairService key_pair_service:
        """
        self.key_pair_service = key_pair_service

    def run_command(self, logger, api, command, context, use_public_ip_str, sandbox_id, aws_clients,
                    aws_ec2_resource_model, cancellation_context):
        """
        :param logging.Logger logger:
        :param CloudShellAPISession api:
        :param str command:
        :param str use_public_ip_str:
        :param ResourceRemoteCommandContext context:
        :param str sandbox_id:
        :param AwsApiClients aws_clients:
        :param AWSEc2CloudProviderResourceModel aws_ec2_resource_model:
        :param CancellationContext cancellation_context:
        :rtype: str
        """
        logger.debug('Running command: "{}"'.format(command))

        target = context.remote_endpoints[0]
        use_public_ip = self._convert_to_bool(use_public_ip_str)

        request = self._build_request(api, aws_clients, aws_ec2_resource_model, command, sandbox_id, target,
                                      use_public_ip)
        json_request = json.dumps(request)

        return CustomScriptShell().execute_command(context, json_request, cancellation_context)

    def _build_request(self, api, aws_clients, aws_ec2_resource_model, command, sandbox_id, target, use_public_ip):
        target_ip = self._get_target_ip(target, use_public_ip)
        username = self._get_target_username(target)
        password = self._get_target_password(target, api)
        ssh_key = None if password else self._get_ssh_key(sandbox_id, aws_clients, aws_ec2_resource_model)
        connection_method = self._get_connection_method(target, api)

        # build request
        request = {
            'commandInfo': {'cmd': command},
            'hostsDetails': [{
                'ip': target_ip,
                'username': username,
                'password': password,
                'access_key': ssh_key,
                'connection_secured': None,
                'connectionMethod': connection_method
            }],
            'timeout_minutes': 10
        }
        return request

    def _get_connection_method(self, target, api):
        """
        :param ResourceContextDetails target:
        :param CloudShellAPISession api:
        :return: ssh/rdp
        """
        resource_details = api.GetResourceDetails(target.name)
        platform =\
            next(iter(filter(lambda x: x.Name.lower() == 'platform', resource_details.VmDetails.InstanceData))).Value

        return 'rdp' if platform.lower() == 'windows' else 'ssh'

    def _get_target_username(self, target):
        """
        :param ResourceContextDetails target:
        :rtype: str
        """
        if USER_ATTR in target.attributes:
            return target.attributes[USER_ATTR]

        user_2nd_gen_attr = self._format_2nd_gen_attr_name(target, USER_ATTR)
        if user_2nd_gen_attr in target.attributes:
            return target.attributes[user_2nd_gen_attr]

        raise Exception("Failed to find user attribute")

    def _get_target_password(self, target, api):
        """
        :param ResourceContextDetails target:
        :param CloudShellAPISession api:
        :rtype: str
        """
        password_encrypted = None

        if USER_ATTR in target.attributes:
            password_encrypted = target.attributes[PASSWORD_ATTR]

        user_2nd_gen_attr = self._format_2nd_gen_attr_name(target, PASSWORD_ATTR)
        if user_2nd_gen_attr in target.attributes:
            password_encrypted = target.attributes[user_2nd_gen_attr]

        if password_encrypted:
            return api.DecryptPassword(password_encrypted).Value

        return None

    def _get_ssh_key(self, sandbox_id, aws_clients, aws_ec2_resource_model):
        """
        :param str sandbox_id:
        :param AwsApiClients aws_clients:
        :param AWSEc2CloudProviderResourceModel aws_ec2_resource_model:
        :return:
        """
        # Password attribute is empty or password attribute is not found. Going to use ssh key
        return self.key_pair_service.load_key_pair_by_name(aws_clients.s3_session,
                                                           aws_ec2_resource_model.key_pairs_location,
                                                           sandbox_id)

    def _get_target_ip(self, target, use_public_ip):
        """
        :param ResourceContextDetails target:
        :param bool use_public_ip:
        :rtype: str
        """
        if not use_public_ip:
            return target.address

        if PUBLIC_IP_ATTR in target.attributes:
            return target.attributes[PUBLIC_IP_ATTR]

        public_ip_2nd_gen_attr = self._format_2nd_gen_attr_name(target, PUBLIC_IP_ATTR)
        if public_ip_2nd_gen_attr in target.attributes:
            return target.attributes[public_ip_2nd_gen_attr]

        raise Exception("Cannot find target IP")

    @staticmethod
    def _format_2nd_gen_attr_name(target, attribute_name):
        return '{}.{}'.format(target.model, attribute_name)

    @staticmethod
    def _convert_to_bool(use_public_ip_str):
        return True if use_public_ip_str.lower() == "true" else False
