import traceback

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
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

    def __init__(self, ec2_session, ec2_client, cancellation_service, vpc_service, subnet_service, tag_service, subnet_waiter):
        """
        :param object ec2_session:
        :param object ec2_client:
        :param CommandCancellationService cancellation_service:
        :param VPCService vpc_service:
        :param SubnetService subnet_service:
        :param TagService tag_service:
        :param SubnetWaiter subnet_waiter:
        """
        self.ec2_session = ec2_session
        self.ec2_client = ec2_client
        self.cancellation_service = cancellation_service
        self.vpc_service = vpc_service
        self.subnet_service = subnet_service
        self.tag_service = tag_service
        self.subnet_waiter = subnet_waiter

    def execute(self, subnet_actions, reservation, aws_ec2_datamodel, ec2_session, ec2_client, cancellation_context, logger):
        self._validate_actions(subnet_actions)
        action_items = map(lambda a: PrepareSubnetExecutor.ActionItem(a), subnet_actions)

        # get vpc and availability_zone
        self.cancellation_service.check_if_cancelled(cancellation_context)
        vpc = self._get_or_throw_vpc()
        availability_zone = self.vpc_service.get_or_pick_availability_zone(self.ec2_client, vpc, aws_ec2_datamodel)

        # get existing subnet bt their cidr
        self.cancellation_service.check_if_cancelled(cancellation_context)
        for item in self._filter_no_error(action_items):
            self._step_get_existing_subnet(item, vpc, logger)

        # create new subnet for the non-existing ones
        self.cancellation_service.check_if_cancelled(cancellation_context)
        for item in self._filter_no_error(action_items):
            if not item.subnet:
                self._step_create_new_subnet(item, vpc, logger, availability_zone)

        # wait for the new ones to be available
        self.cancellation_service.check_if_cancelled(cancellation_context)
        for item in self._filter_no_error(action_items):
            if item.is_new_subnet:
                self._step_wait_till_available(item, logger)

        # add tags
        self.cancellation_service.check_if_cancelled(cancellation_context)
        for item in self._filter_no_error(action_items):
            self._step_set_tags(item, logger, reservation)

        # set non-public subnets with private route table
        for item in self._filter_no_error(action_items):
            if not item.action.connection_params.is_public:
                self._step_attach_to_private_route_table(item, vpc, logger, reservation, ec2_session, ec2_client)

        return [self._create_result(item) for item in action_items]

    def _validate_actions(self, subnet_actions):
        if any(not isinstance(a.connection_params, PrepareSubnetParams) for a in subnet_actions):
            raise ValueError("Not all actions are PrepareSubnetActions")

    def _get_or_throw_vpc(self):
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=self.ec2_session, reservation_id=self.reservation.reservation_id)
        if not vpc:
            raise ValueError('Vpc for reservation {0} not found.'.format(self.reservation.reservation_id))

    def _filter_no_error(self, items):
        return [i for i in items if not i.error]

    def _step_get_existing_subnet(self, item, vpc, logger):
        try:
            cidr = item.action.connection_params.cidr
            logger.info("Check if subnet (cidr={0}) already exists".format(cidr));
            item.subnet = self.subnet_service.get_first_or_none_subnet_from_vpc(vpc=vpc, cidr=cidr)
        except Exception as e:
            logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
            item.error = e

    def _step_create_new_subnet(self, item, vpc, logger, availability_zone):
        try:
            cidr = item.action.connection_params.cidr
            logger.info("Create subnet (alias: {0}, cidr: {1}, availability-zone: {2})".format(cidr, availability_zone))
            item.subnet = self.subnet_service.create_subnet_nowait(vpc, cidr, availability_zone)
            item.is_new_subnet = True
        except Exception as e:
            logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
            item.error = e

    def _step_wait_till_available(self, item, logger):
        logger.info("Waiting for subnet {0}".format(item.action.connection_params.cidr))
        self.subnet_waiter.wait(item.subnet, self.subnet_waiter.AVAILABLE)

    def _step_set_tags(self, item, logger, reservation):
        try:
            alias = item.action.connection_params.alias or "Subnet-{0}".format(item.action.connection_params.cidr)
            subnet_name = self.SUBNET_RESERVATION.format(alias, reservation.reservation_id)
            tags = self.tag_service.get_default_tags(subnet_name, reservation)
            self.tag_service.set_ec2_resource_tags(item.subnet, tags)
        except Exception as e:
            logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
            item.error = e

    def _step_attach_to_private_route_table(self, item, vpc, logger, reservation, ec2_session, ec2_client):
        try:
            logger.info("Subnet is private - getting and attaching private routing table")
            private_route_table = self.vpc_service.get_or_throw_private_route_table(ec2_session, reservation, vpc.vpc_id)
            self.subnet_service.set_subnet_route_table(ec2_client=ec2_client,
                                                       subnet_id=item.subnet.subnet_id,
                                                       route_table_id=private_route_table.route_table_id)
        except Exception as e:
            logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
            item.error = e

    def _create_result(self, item):
        action_result = PrepareSubnetActionResult()
        action_result.actionId = item.action.id
        if item.subnet:
            action_result.success = True
            action_result.subnetId = item.subnet.subnet_id
            action_result.infoMessage = 'PrepareSubnet finished successfully'
        else:
            action_result.success = False
            action_result.errorMessage = 'PrepareConnectivity ended with the error: {0}'.format(item.error)
        return action_result