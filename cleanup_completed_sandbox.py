# debug - manual reservation cleanup
import json

import boto3 as boto3
from cloudshell.cp.core.models import RequestActionBase
from mock import Mock

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupSandboxInfraOperation
from cloudshell.cp.aws.domain.context.client_error import ClientErrorWrapper
from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.domain.services.ec2.mirroring import TrafficMirrorService
from cloudshell.cp.aws.domain.services.ec2.route_table import RouteTablesService
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.s3.bucket import S3BucketService
from cloudshell.cp.aws.domain.services.waiters.instance import InstanceWaiter
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc import VPCWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel

client_err_wrapper = ClientErrorWrapper()
tag_service = TagService(client_err_wrapper=client_err_wrapper)
subnet_waiter = SubnetWaiter()
subnet_service = SubnetService(tag_service, subnet_waiter)
cancellation_service = CommandCancellationService()
ec2_instance_waiter = InstanceWaiter(cancellation_service=cancellation_service)
instance_service = InstanceService(tag_service, ec2_instance_waiter)
vpc_waiter = VPCWaiter()
vpc_peering_waiter = VpcPeeringConnectionWaiter()
security_group_service = SecurityGroupService(tag_service)
route_tables_service = RouteTablesService(tag_service)
traffic_mirror_service = TrafficMirrorService()
vpc_service = VPCService(tag_service=tag_service,
                         subnet_service=subnet_service,
                         instance_service=instance_service,
                         vpc_waiter=vpc_waiter,
                         vpc_peering_waiter=vpc_peering_waiter,
                         sg_service=security_group_service,
                         route_table_service=route_tables_service,
                         traffic_mirror_service=traffic_mirror_service)
s3_service = S3BucketService()
key_pair_service = KeyPairService(s3_service)
route_tables_service = RouteTablesService(tag_service)
ec2_model = AWSEc2CloudProviderResourceModel()

operation = CleanupSandboxInfraOperation(vpc_service, key_pair_service, route_tables_service, traffic_mirror_service)

# get info
region = raw_input ("Enter region: ")
sandox_id = raw_input ("Enter sandbox id: ")
ec2_model.key_pairs_location = raw_input ("Enter keypairs bucket name: ")

# init clients
boto_session = boto3.Session(region_name=region)
ec2_session = boto_session.resource('ec2')
s3_session = boto_session.resource('s3')
ec2_client = boto_session.client('ec2')

result = operation.cleanup(ec2_client, ec2_session, s3_session, ec2_model, sandox_id, [RequestActionBase()], Mock())

print result
