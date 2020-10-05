import traceback
import ipaddress
from logging import Logger

from cloudshell.shell.core.driver_context import CancellationContext

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.core.models import PrepareCloudInfraResult
from cloudshell.cp.aws.models.reservation_model import ReservationModel
from cloudshell.cp.core.models import PrepareSubnet


class PrepareSubnetExecutor(object):
    SUBNET_RESERVATION = '{0} Reservation: {1}'

    class ActionItem:
        def __init__(self, action):
            self.action = action  # type: PrepareSubnet
            self.subnet = None
            self.is_new_subnet = False
            self.error = None

    def __init__(self, cancellation_service, vpc_service, subnet_service,
                 tag_service, subnet_waiter, reservation, aws_ec2_datamodel, cancellation_context, logger, ec2_session,
                 ec2_client):
        """
        :param CommandCancellationService cancellation_service:
        :param VPCService vpc_service:
        :param SubnetService subnet_service:
        :param TagService tag_service:
        :param SubnetWaiter subnet_waiter:
        :param ReservationModel reservation:
        :param AWSEc2CloudProviderResourceModel aws_ec2_datamodel:
        :param CancellationContext cancellation_context:
        :param Logger logger:
        :param ec2_session:
        :param ec2_client:
        """
        self.ec2_client = ec2_client
        self.ec2_session = ec2_session
        self.logger = logger
        self.cancellation_context = cancellation_context
        self.aws_ec2_datamodel = aws_ec2_datamodel
        self.reservation = reservation
        self.cancellation_service = cancellation_service
        self.vpc_service = vpc_service
        self.subnet_service = subnet_service
        self.tag_service = tag_service
        self.subnet_waiter = subnet_waiter

    def execute(self, subnet_actions):
        if any(not isinstance(a, PrepareSubnet) for a in subnet_actions):
            raise ValueError("Not all actions are PrepareSubnet")
        action_items = [PrepareSubnetExecutor.ActionItem(a) for a in subnet_actions]

        # get vpc and availability_zone
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=self.ec2_session,
                                                        reservation_id=self.reservation.reservation_id)

        if not vpc:
            vpcs_count = self.vpc_service.get_active_vpcs_count(self.ec2_client, self.logger)
            additional_msg = "\nThere are {0} active VPCs in region \"{1}\"." \
                             "\nPlease make sure you haven't exceeded your region's VPC limit." \
                .format(vpcs_count, self.aws_ec2_datamodel.region) if vpcs_count else ""
            raise ValueError('VPC for reservation {0} not found.{1}'.format(self.reservation.reservation_id,
                                                                            additional_msg))

        availability_zone = self.vpc_service.get_or_pick_availability_zone(self.ec2_client, vpc, self.aws_ec2_datamodel)

        is_multi_subnet_mode = len(action_items) > 1  # type: bool

        # get existing subnet bt their cidr
        for item in action_items:
            self._step_get_existing_subnet(item, vpc, is_multi_subnet_mode)

        # create new subnet for the non-existing ones
        for item in action_items:
            self._step_create_new_subnet_if_needed(item, vpc, availability_zone, is_multi_subnet_mode)

        # wait for the new ones to be available
        for item in action_items:
            self._step_wait_till_available(item)

        # set tags
        for item in action_items:
            self._step_set_tags(item)

        # set non-public subnets with private route table
        for item in action_items:
            self._step_attach_to_private_route_table(item, vpc)

        return [self._create_result(item) for item in action_items]

    # DECORATOR! First argument is the decorated function!
    def step_wrapper(step):
        def wrapper(self, item, *args, **kwargs):
            self.cancellation_service.check_if_cancelled(self.cancellation_context)
            if item.error:
                return
            try:
                step(self, item, *args, **kwargs)
            except Exception as e:
                self.logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
                item.error = e

        return wrapper

    @step_wrapper
    def _step_get_existing_subnet(self, item, vpc, is_multi_subnet_mode):
        sah = SubnetActionHelper(item.action.actionParams, self.aws_ec2_datamodel, self.logger, is_multi_subnet_mode)
        cidr = sah.cidr
        self.logger.info("Check if subnet (cidr={0}) already exists".format(cidr))
        item.subnet = self.subnet_service.get_first_or_none_subnet_from_vpc(vpc=vpc, cidr=cidr)

    @step_wrapper
    def _step_create_new_subnet_if_needed(self, item, vpc, availability_zone, is_multi_subnet_mode):
        if not item.subnet:
            sah = SubnetActionHelper(item.action.actionParams,
                                     self.aws_ec2_datamodel,
                                     self.logger,
                                     is_multi_subnet_mode)
            cidr = sah.cidr
            item.cidr = sah.cidr
            alias = item.action.actionParams.alias
            self.logger.info("Create subnet (alias: {0}, cidr: {1}, availability-zone: {2})"
                             .format(alias, cidr, availability_zone))
            item.subnet = self.subnet_service.create_subnet_nowait(vpc, cidr, availability_zone)
            item.is_new_subnet = True

    @step_wrapper
    def _step_wait_till_available(self, item):
        if item.is_new_subnet:
            self.logger.info("Waiting for subnet {0} - start".format(item.action.actionParams.cidr))
            self.subnet_waiter.wait(item.subnet, self.subnet_waiter.AVAILABLE)
            self.logger.info("Waiting for subnet {0} - end".format(item.action.actionParams.cidr))

    @step_wrapper
    def _step_set_tags(self, item):
        alias = item.action.actionParams.alias or "Subnet-{0}".format(item.action.actionParams.cidr)
        subnet_name = self.SUBNET_RESERVATION.format(alias, self.reservation.reservation_id)
        is_public_tag = self.tag_service.get_is_public_tag(item.action.actionParams.isPublic)
        tags = self.tag_service.get_default_tags(subnet_name, self.reservation)
        tags.append(is_public_tag)
        self.tag_service.set_ec2_resource_tags(item.subnet, tags)

    @step_wrapper
    def _step_attach_to_private_route_table(self, item, vpc):
        if item.action.actionParams.isPublic:
            self.logger.info("Subnet is public - no need to attach private routing table")
        else:
            self.logger.info("Subnet is private - getting and attaching private routing table")
            private_route_table = self.vpc_service.get_or_throw_private_route_table(self.ec2_session, self.reservation,
                                                                                    vpc.vpc_id)
            self.subnet_service.set_subnet_route_table(ec2_client=self.ec2_client,
                                                       subnet_id=item.subnet.subnet_id,
                                                       route_table_id=private_route_table.route_table_id)

    def _create_result(self, item):
        action_result = PrepareCloudInfraResult()
        action_result.actionId = item.action.actionId
        if item.subnet and not item.error:
            action_result.success = True
            action_result.subnetId = item.subnet.subnet_id
            action_result.infoMessage = 'PrepareSubnet finished successfully'
        else:
            action_result.success = False
            action_result.errorMessage = 'PrepareSandboxInfra ended with the error: {0}'.format(item.error)
        return action_result


class SubnetActionHelper(object):
    def __init__(self, prepare_subnet_params, aws_cp_model, logger, is_multi_subnet_mode):
        """
        SubnetActionHelper decides what CIDR to use, a requested CIDR from attribute, if exists, or from Server
        and also whether to Enable Nat, & Route traffic through the NAT

        :param cloudshell.cp.core.models.PrepareSubnetParams prepare_subnet_params:
        :param AWSEc2CloudProviderResourceModel aws_cp_model:
        :param Logger logger:
        """

        # VPC CIDR is determined as follows:
        # if in VPC static mode and its a single subnet mode, use VPC CIDR
        # if in VPC static mode and its multi subnet mode, we must assume its manual subnets and use action CIDR
        # else, use action CIDR
        # alias = prepare_subnet_params.alias if hasattr(prepare_subnet_params, 'alias') else 'Default Subnet'
        alias = getattr(prepare_subnet_params, 'alias', 'Default Subnet')

        if aws_cp_model.is_static_vpc_mode and aws_cp_model.vpc_cidr != '' and not is_multi_subnet_mode:
            self._cidr = aws_cp_model.vpc_cidr
            logger.info('Decided to use VPC CIDR {0} as defined on cloud provider for subnet {1}'
                        .format(self._cidr, alias))
        else:
            self._cidr = prepare_subnet_params.cidr
            logger.info('Decided to use VPC CIDR {0} as defined on subnet request for subnet {1}'
                        .format(self._cidr, alias))

    @property
    def cidr(self):
        return self._cidr
