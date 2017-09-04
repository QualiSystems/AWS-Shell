import traceback
from logging import Logger

from cloudshell.shell.core.driver_context import CancellationContext

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.connectivity_models import PrepareSubnetActionResult
from cloudshell.cp.aws.models.network_actions_models import NetworkAction, PrepareSubnetParams
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class PrepareSubnetExecutor(object):
    SUBNET_RESERVATION = '{0} Reservation: {1}'

    class ActionItem:
        def __init__(self, action):
            self.action = action # type: NetworkAction
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
        if any(not isinstance(a.connection_params, PrepareSubnetParams) for a in subnet_actions):
            raise ValueError("Not all actions are PrepareSubnetActions")
        action_items = [PrepareSubnetExecutor.ActionItem(a) for a in subnet_actions]

        # get vpc and availability_zone
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=self.ec2_session, reservation_id=self.reservation.reservation_id)
        if not vpc:
            raise ValueError('Vpc for reservation {0} not found.'.format(self.reservation.reservation_id))
        availability_zone = self.vpc_service.get_or_pick_availability_zone(self.ec2_client, vpc, self.aws_ec2_datamodel)

        # get existing subnet bt their cidr
        for item in action_items:
            self._step_get_existing_subnet(item, vpc)

        # create new subnet for the non-existing ones
        for item in action_items:
            self._step_create_new_subnet_if_needed(item, vpc, availability_zone)

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
    def _step_get_existing_subnet(self, item, vpc):
        cidr = item.action.connection_params.cidr
        self.logger.info("Check if subnet (cidr={0}) already exists".format(cidr))
        item.subnet = self.subnet_service.get_first_or_none_subnet_from_vpc(vpc=vpc, cidr=cidr)

    @step_wrapper
    def _step_create_new_subnet_if_needed(self, item, vpc, availability_zone):
        if not item.subnet:
            cidr = item.action.connection_params.cidr
            alias = item.action.connection_params.alias
            self.logger.info("Create subnet (alias: {0}, cidr: {1}, availability-zone: {2})".format(alias, cidr, availability_zone))
            item.subnet = self.subnet_service.create_subnet_nowait(vpc, cidr, availability_zone)
            item.is_new_subnet = True

    @step_wrapper
    def _step_wait_till_available(self, item):
        if item.is_new_subnet:
            self.logger.info("Waiting for subnet {0} - start".format(item.action.connection_params.cidr))
            self.subnet_waiter.wait(item.subnet, self.subnet_waiter.AVAILABLE)
            self.logger.info("Waiting for subnet {0} - end".format(item.action.connection_params.cidr))

    @step_wrapper
    def _step_set_tags(self, item):
        alias = item.action.connection_params.alias or "Subnet-{0}".format(item.action.connection_params.cidr)
        subnet_name = self.SUBNET_RESERVATION.format(alias, self.reservation.reservation_id)
        is_public_tag = self.tag_service.get_is_public_tag(item.action.connection_params.is_public)
        tags = self.tag_service.get_default_tags(subnet_name, self.reservation)
        tags.append(is_public_tag)
        self.tag_service.set_ec2_resource_tags(item.subnet, tags)

    @step_wrapper
    def _step_attach_to_private_route_table(self, item, vpc):
        if item.action.connection_params.is_public:
            self.logger.info("Subnet is public - no need to attach private routing table")
        else:
            self.logger.info("Subnet is private - getting and attaching private routing table")
            private_route_table = self.vpc_service.get_or_throw_private_route_table(self.ec2_session, self.reservation, vpc.vpc_id)
            self.subnet_service.set_subnet_route_table(ec2_client=self.ec2_client,
                                                       subnet_id=item.subnet.subnet_id,
                                                       route_table_id=private_route_table.route_table_id)

    def _create_result(self, item):
        action_result = PrepareSubnetActionResult()
        action_result.actionId = item.action.id
        if item.subnet and not item.error:
            action_result.success = True
            action_result.subnetId = item.subnet.subnet_id
            action_result.infoMessage = 'PrepareSubnet finished successfully'
        else:
            action_result.success = False
            action_result.errorMessage = 'PrepareConnectivity ended with the error: {0}'.format(item.error)
        return action_result

