import traceback

import botocore
from botocore.exceptions import WaiterError
from concurrent.futures._base import wait

from cloudshell.cp.aws.common import retry_helper


class InstanceService(object):
    def __init__(self, tags_creator_service, instance_waiter):
        """
        :param tags_creator_service: Tags Service
        :type tags_creator_service: cloudshell.cp.aws.domain.services.tags.TagService
        :param instance_waiter: Instance Waiter
        :type instance_waiter: cloudshell.cp.aws.domain.services.waiters.instance.InstanceWaiter
        """
        self.instance_waiter = instance_waiter
        self.tags_creator_service = tags_creator_service

    def create_instance(self, ec2_session, name, reservation, ami_deployment_info, ec2_client, wait_for_status_check,
                        logger):
        """
        Deploys an AMI
        :param logger: logger
        :param wait_for_status_check: bool
        :param ec2_client: boto3.ec2.client
        :param name: Will assign the deployed vm with the name
        :type name: str
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param ec2_session:
        :type ec2_session: boto3.ec2.session
        :param ami_deployment_info: request details of the AMI
        :type ami_deployment_info: cloudshell.cp.aws.models.ami_deployment_model.AMIDeploymentModel
        :return:
        """
        instance = ec2_session.create_instances(
            ImageId=ami_deployment_info.aws_ami_id,
            MinCount=ami_deployment_info.min_count,
            MaxCount=ami_deployment_info.max_count,
            InstanceType=ami_deployment_info.instance_type,
            KeyName=ami_deployment_info.aws_key,
            BlockDeviceMappings=ami_deployment_info.block_device_mappings,
            NetworkInterfaces=[
                {
                    'SubnetId': ami_deployment_info.subnet_id,
                    'DeviceIndex': 0,
                    'Groups': ami_deployment_info.security_group_ids,
                    'AssociatePublicIpAddress': ami_deployment_info.add_public_ip
                }]
            # PrivateIpAddress=ami_deployment_info.private_ip_address
        )[0]

        self.wait_for_instance_to_run_in_aws(ec2_client, instance, wait_for_status_check, logger)

        self._set_tags(instance, name, reservation)

        # Reload the instance attributes
        retry_helper.do_with_retry(lambda: instance.load())
        return instance

    def wait_for_instance_to_run_in_aws(self, ec2_client, instance, wait_for_status_check, logger):
        if wait_for_status_check:
            try:
                ec2_client.get_waiter('instance_status_ok') \
                    .wait(InstanceIds=[instance.instance_id])
            except WaiterError as e:
                logger.error("Error in wait_for_instance_to_run_in_aws, instance status in not OK. Error: {0}"
                             .format(traceback.format_exc()))
                raise ValueError('Instance status check is not OK. Check the log and aws console for more details.')
            logger.info("Instance created with status: instance_status_ok.")
        else:
            instance.wait_until_running()

    def terminate_instance(self, instance):
        return self.terminate_instances([instance])[0]

    def terminate_instances(self, instances):
        if len(instances) == 0:
            return

        for instance in instances:
            instance.terminate()
        return self.instance_waiter.multi_wait(instances, self.instance_waiter.TERMINATED)

    def associate_elastic_ip(self, ec2_session, instance, elastic_ip):
        """
        Assign an elastic ip to the primary interface and primary private ip of the given instance
        :param ec2_session:
        :param instance:
        :param str elastic_ip: The allocation ID
        :return:
        """
        response = list(ec2_session.vpc_addresses.filter(PublicIps=[elastic_ip]))
        if len(response) == 1:
            vpc_address = response[0]
            vpc_address.associate(InstanceId=instance.id, AllowReassociation=False)
        else:
            raise ValueError("Failed to find elastic ip {0} allocation id".format(elastic_ip))

    def _set_tags(self, instance, name, reservation):
        # todo create the name with a name generator
        new_name = name + ' ' + instance.instance_id
        default_tags = self.tags_creator_service.get_default_tags(new_name, reservation)
        self.tags_creator_service.set_ec2_resource_tags(instance, default_tags)

    @staticmethod
    def get_instance_by_id(ec2_session, id):
        instance = ec2_session.Instance(id=id)
        if not hasattr(instance, "state") or instance.state['Name'].lower() == 'terminated':
            raise Exception("Can't perform action. EC2 instance was terminated/removed")

        return instance

    @staticmethod
    def allocate_elastic_address(ec2_client):
        """
        :param ec2_client:
        :return:
        """
        result = ec2_client.allocate_address(Domain='vpc')
        return result["PublicIp"]

    @staticmethod
    def release_elastic_address(vpc_address):
        """
        :param vpc_address:
        """
        vpc_address.release()
