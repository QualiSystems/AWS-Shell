import itertools
import json
import time
from collections import defaultdict

from jsonschema import validate

from cloudshell.cp.aws.domain.common.CheckCancellationThread import CheckCancellationThread
from cloudshell.cp.aws.domain.conncetivity.operations.traffic_mirror_cleaner import TrafficMirrorCleaner
from cloudshell.cp.aws.models.traffic_mirror_fulfillment import TrafficMirrorFulfillment, create_results
from cloudshell.cp.core.models import RemoveTrafficMirroringResult
from cloudshell.cp.aws.domain.services.ec2.mirroring import TrafficMirrorService

flatten = itertools.chain.from_iterable


class TrafficMirrorOperation(object):
    def __init__(self, tag_service, session_number_service, traffic_mirror_service, cancellation_service):
        """
        :type cloudshell.cp.aws.domain.services.ec2.mirroring.TrafficMirrorService traffic_mirror_service:
        :param cloudshell.cp.aws.domain.common.cancellation_service.CommandCancellationService cancellation_service: object
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        :param cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services.SessionNumberService session_number_service:
        """
        self._tag_service = tag_service
        self._session_number_service = session_number_service
        self._traffic_mirror_service = traffic_mirror_service  # type: TrafficMirrorService
        self._cancellation_service = cancellation_service

    def _handle_cancellation(self, cancellation_context):
        while True:
            time.sleep(1)
            cancelled = self._cancellation_service.check_if_cancelled(cancellation_context)
            if cancelled:
                raise Exception('User cancelled traffic mirroring')

    def create(self,
               ec2_client,
               reservation,
               actions,
               cancellation_context,
               logger,
               cloudshell):
        """
        :param cloudshell.shell.core.driver_context.CancellationContext cancellation_context:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param EC2.Client ec2_client:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions: what traffic mirroring sessions,
               targets and filters to apply
        :param logging.Logger logger:
        :return:
        """

        success = False

        logger.info('Received request to deploy traffic mirroring. ')

        action_parameters_string = self._get_action_parameters_string(actions)
        logger.info(action_parameters_string)

        # session numbers: session number is the AWS priority of a traffic mirror session; the lower a session number,
        # the earlier it gets the opportunity to capture traffic from a source nic.
        # anyways, session numbers MUST be unique; to provide this behavior, we are using cloudshell pool checkout
        # to read more about session numbers, go here: https://docs.aws.amazon.com/vpc/latest/mirroring/traffic-mirroring-session.html
        # to read more about cloudshell pools, go here: https://help.quali.com/Online%20Help/0.0/TestShell-API/TestShell%20Python%20API.html#CheckoutFromPool
        self._checkout_session_numbers(actions, cloudshell, logger, reservation)

        fulfillments = [TrafficMirrorFulfillment(x, reservation) for x in actions]

        logger.info('Determined session numbers: ' + ', '.join(str(f.session_number) for f in fulfillments))

        success = False

        try:
            with CheckCancellationThread(cancellation_context, self._cancellation_service):
                logger.info('Getting or creating traffic mirror targets...')
                self._get_or_create_targets(ec2_client,
                                            reservation,
                                            fulfillments)

                logger.info('Creating traffic mirror filters and sessions...')
                self._create_traffic_filters_and_sessions(ec2_client,
                                                          fulfillments)
                # self._get_or_create_sessions(ec2_client,
                #                              fulfillments)

            success = True
            message = 'Success'
            logger.info('Successfully fulfilled traffic mirror request')

        except Exception as e:
            logger.exception('Failed to fulfill traffic mirror request: ' + e.message)
            message = e.message
            logger.error('Rolling back partial traffic mirror request...')
            TrafficMirrorCleaner.rollback(ec2_client, fulfillments, logger, cloudshell, reservation,
                                          self._session_number_service)

        results = create_results(success, fulfillments, message)
        return results

    def _get_action_parameters_string(self, actions):
        return 'Here are the params:\n' + '\n'.join(str(x) for x in actions)

    def _get_or_create_targets(self, ec2_client, reservation, fulfillments):
        """
        create traffic mirror targets for target nics OR find existing targets that correspond
        to target nic in fulfillment

        :param list[cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment] fulfillments:
        """
        target_nics = list({f.target_nic_id for f in fulfillments})
        targets_found_nics_to_target_id = self._traffic_mirror_service.find_traffic_targets_by_nics(ec2_client,
                                                                                                    target_nics)
        self._create_targets_or_assign_existing_targets(ec2_client,
                                                        targets_found_nics_to_target_id,
                                                        self._tag_service,
                                                        reservation,
                                                        fulfillments)

    def _create_traffic_filters_and_sessions(self, ec2_client, fulfillments):
        """
        :param list[cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment] fulfillments:
        """
        for fulfillment in fulfillments:
            self._create_filter(ec2_client, fulfillment)
            fulfillment.mirror_session_id = self._create_session(ec2_client, fulfillment)

    def _get_or_create_sessions(self, ec2_client, fulfillments):
        """
        :param list[cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment] fulfillments:
        """
        session_names = [f.session_name for f in fulfillments]
        session_name_to_found_session = self._traffic_mirror_service.find_sessions_by_session_names(ec2_client,
                                                                                                    session_names)
        found_session_names = session_name_to_found_session.keys()

        for s in session_names:
            fulfillment = next((f for f in fulfillments if f.session_name == s))

            if s not in found_session_names:
                self._create_filter(ec2_client, fulfillment)
                fulfillment.mirror_session_id = self._create_session(ec2_client, fulfillment)
            else:
                fulfillment.mirror_session_id = session_name_to_found_session[s]['TrafficMirrorSessionId']

    def _create_targets_or_assign_existing_targets(self, ec2_client,
                                                   nics_to_found_target_ids,
                                                   tag_service,
                                                   reservation,
                                                   fulfillments):
        """
        :param list[cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment] fulfillments:
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        """
        target_nics_to_fulfillments = defaultdict(list)
        [target_nics_to_fulfillments[f.target_nic_id].append(f) for f in fulfillments]

        for target_nic in target_nics_to_fulfillments.keys():
            if target_nic not in nics_to_found_target_ids:
                target_tags = tag_service.get_default_tags(target_nic, reservation)
                target = self._traffic_mirror_service.create_traffic_mirror_target_from_nic(ec2_client, target_nic,
                                                                                            target_tags)
                self._assign_target_to_fulfillments(target_nics_to_fulfillments[target_nic], target)
            else:
                self._assign_target_to_fulfillments(target_nics_to_fulfillments[target_nic],
                                                    nics_to_found_target_ids[target_nic])

    @staticmethod
    def _assign_target_to_fulfillments(fulfillments, traffic_target_id):
        for fulfillment in fulfillments:
            fulfillment.traffic_mirror_target_id = traffic_target_id

    def _create_session(self, ec2_client, fulfillment):
        """
        :param cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment fulfillment:
        """
        mirror_session_tags = self._tag_service.get_default_tags('session-' + fulfillment.session_name,
                                                                 fulfillment.reservation)

        return self._traffic_mirror_service.create_traffic_mirror_session(ec2_client, fulfillment, mirror_session_tags)

    def _create_filter(self, ec2_client, fulfillment):
        traffic_filter_tags = self._tag_service.get_default_tags('filter-' + fulfillment.session_name,
                                                                 fulfillment.reservation)
        fulfillment.traffic_mirror_filter_id = \
            self._traffic_mirror_service.create_filter(ec2_client, traffic_filter_tags)
        self._traffic_mirror_service.create_filter_rules(ec2_client, fulfillment)

    def validate_create_actions(self, actions, request, logger):
        """
        :param str request:
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions:
        """
        self._there_are_actions(actions)
        result = json.loads(request)
        for a in result['driverRequest']['actions']:
            self._validate_schema(CREATE_SCHEMA, a)
        self._there_are_source_and_target_nics(actions)
        self._session_numbers_are_valid(actions, logger)  # must be 1-32766 or NONE

    def _there_are_source_and_target_nics(self, actions):
        for a in actions:
            if not a.actionParams.sourceNicId:
                raise Exception('Missing a source nic on actionId {0}'.format(a.actionId))
            if not a.actionParams.targetNicId:
                raise Exception('Missing a target nic on actionId {0}'.format(a.actionId))

    def _there_are_actions(self, actions):
        if len(actions) == 0:
            raise Exception('Invalid request')

    def _checkout_session_numbers(self, actions, cloudshell, logger, reservation):
        """
        session number must be between 1-32766 and unique per source nic id;
        every traffic mirror session must have a number assigned
        the number represents the priority of a target when pulling the traffic packets.

        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions:
        """

        source_nic_to_traffic_action = defaultdict(list)
        [source_nic_to_traffic_action[a.actionParams.sourceNicId].append(a) for a in actions]
        for source in source_nic_to_traffic_action.keys():
            self.get_unique_session_number_and_assign_to_mirror_session_request(cloudshell, logger, reservation, source,
                                                                                source_nic_to_traffic_action)

    def get_unique_session_number_and_assign_to_mirror_session_request(self, cloudshell, logger, reservation, source,
                                                                       source_nic_to_traffic_action):
        for action in source_nic_to_traffic_action[source]:
            session_number = action.actionParams.sessionNumber
            action.actionParams.sessionNumber = self._session_number_service.checkout(cloudshell,
                                                                                      logger,
                                                                                      reservation,
                                                                                      source,
                                                                                      session_number)

    @staticmethod
    def _session_numbers_are_valid(actions, logger):
        """
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions:
        :param logging.Logger logger:
        """
        error_msg = 'Session number must be either empty or an integer in the range 1-32766'

        # must be 1-32766 or NONE
        for a in actions:
            try:
                session_number = int(a.actionParams.sessionNumber)
                if session_number and \
                        not isinstance(session_number, (int, long)) \
                        or session_number > 32766 \
                        or session_number < 1:
                    logger.error(error_msg + '\nSession number is {0}'.format(session_number))
                    raise Exception(error_msg)
            except ValueError:
                if a.actionParams.sessionNumber.strip() == '':
                    a.actionParams.sessionNumber = None
                else:
                    raise ValueError(
                        'Session number must be an integer, or an empty string! Passed an invalid session number {0} in action {1}'
                            .format(a.actionParams.sessionNumber, a.actionId))

    def remove(self, ec2_client, reservation, actions, logger, cloudshell):
        """
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param EC2.Client ec2_client:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param list[cloudshell.cp.core.models.RemoveTrafficMirroring] actions:
        :param logging.Logger logger:
        :return:
        """
        logger.info('Received request to remove traffic mirroring. ')

        remove_results = [RemoveTrafficMirroringResult(
            actionId=a.actionId,
            success=False
        ) for a in actions]

        try:
            logger.info('Finding sessions to remove...')

            sessions = self._find_sessions_to_remove(ec2_client, actions)

            if not len(sessions) > 0:
                raise Exception('No sessions found to remove!')

            logger.info('Removing sessions and release...')

            session_ids = [s['TrafficMirrorSessionId'] for s in sessions]

            TrafficMirrorCleaner.delete_mirror_sessions(
                ec2_client,
                session_ids
            )

            self._releasing_session_numbers(cloudshell, reservation, ec2_client, logger, sessions)

            traffic_mirror_filter_ids = [s['TrafficMirrorFilterId'] for s in sessions]
            if len(traffic_mirror_filter_ids) > 0:
                logger.info('Removing filters...')
                TrafficMirrorCleaner.delete_mirror_filters(ec2_client, traffic_mirror_filter_ids)

            logger.info('Successfully removed traffic mirroring')
            for res in remove_results:
                res.success = True
                res.infoMessage = 'Found sessions: {0}.'.format(', '.join(session_ids))

        except Exception as e:
            logger.exception('Failed to remove traffic mirroring: ' + e.message)
            for res in remove_results:
                res.errorMessage = 'Failed to remove traffic mirroring: ' + e.message

        return remove_results

    def _releasing_session_numbers(self, cloudshell, reservation, ec2_client, logger, sessions):
        session_numbers = [str(s['SessionNumber']) for s in sessions]
        traffic_mirror_session_network_interface_id = next((s['NetworkInterfaceId'] for s in sessions))
        TrafficMirrorCleaner.release_session_numbers_from_pool_by_session_ids_and_network_interface_id(
            cloudshell,
            self._session_number_service,
            logger,
            reservation,
            session_numbers,
            traffic_mirror_session_network_interface_id
        )

    def _find_sessions_to_remove(self, ec2_client, actions):
        sessions = []
        session_ids_from_request = [a.sessionId for a in actions if a.sessionId]
        sessions.extend(
            self._traffic_mirror_service.find_sessions_by_session_ids(ec2_client, session_ids_from_request)
        )
        traffic_mirror_target_nic_ids = [a.targetNicId for a in actions if a.targetNicId]
        traffic_mirror_target_ids = self._traffic_mirror_service.find_traffic_mirror_target_ids_by_target_nic_ids(
            ec2_client, traffic_mirror_target_nic_ids)

        sessions.extend(
            self._traffic_mirror_service.find_sessions_by_traffic_mirror_target_ids(ec2_client,
                                                                                    traffic_mirror_target_ids)
        )

        unique_sessions = {s['TrafficMirrorSessionId']: s for s in sessions}

        return unique_sessions.values()

    @staticmethod
    def validate_remove_request(request, logger):
        """
        :param str request:
        """
        logger.info('Validating requested actions...')

        result = json.loads(request)

        actions = result['driverRequest']['actions']

        if len(actions) == 0:
            raise Exception('Invalid request, expected remove actions but none found')

        for a in actions:
            TrafficMirrorOperation._validate_schema(REMOVE_SCHEMA, a)

            if not a['sessionId'] and not a['targetNicId']:
                raise Exception(
                    'Must have either sessionId or target_nic_id for actionId {0} but received empty values'.format(a.actionId))

        logger.info('Completed validation for Remove Traffic Mirroring request...')

    def find_traffic_mirror_target_nic_id_by_target_id(self, ec2_client, traffic_mirror_target_id):
        return self._traffic_mirror_service.find_traffic_mirror_target_nic_id_by_target_id(ec2_client,
                                                                                           traffic_mirror_target_id)

    @staticmethod
    def _validate_schema(schema, action):
        """
        :param cloudshell.cp.core.models.RequestActionBase action:
        :return:
        """

        validate(action, schema)


REMOVE_SCHEMA = {
    "$id": "https://example.com/geographical-location.schema.json",
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "RemoveTrafficMirroring",
    "required": ["actionId", "sessionId", "targetNicId"],
    "additionalProperties": False,
    "properties": {
        "type": {"type": "string"},
        "actionId": {"type": "string"},
        "sessionId": {"type": "string"},
        "targetNicId": {"type": "string"}
    }
}

CREATE_SCHEMA = {
    "$id": "https://example.com/geographical-location.schema.json",
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CreateTrafficMirroring",
    "type": "object",
    "additionalProperties": False,
    "required": ["actionId", "actionParams"],
    "definitions": {
        "CreateTrafficMirroringParams": {
            "title": "CreateTrafficMirroringParams",
            "type": "object",
            "additionalProperties": False,
            "required": ["sourceNicId", "targetNicId"],
            "properties": {
                "type": {"type": "string"},
                "sourceNicId": {
                    "type": "string"
                },
                "targetNicId": {
                    "type": "string"
                },
                "sessionNumber": {
                    "type": "string"
                },
                "filterRules": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/filterRule"
                    }
                }
            }},
        "filterRule": {
            "type": "object",
            "additionalProperties": False,
            "required": ["direction", "protocol"],
            "properties": {
                "type": {"type": "string"},
                "direction": {
                    "type": "string"
                },
                "destinationCidr": {
                    "type": "string"
                },
                "destinationPortRange": {
                    "type": ["object", "null"]
                },
                "sourceCidr": {
                    "type": "string"
                },
                "sourcePortRange": {
                    "type": ["object", "null"]
                },
                "protocol": {
                    "type": "string"
                }
            }
        }
    },
    "properties": {
        "actionId": {
            "type": "string",
        },
        "type": {"type": "string"},
        "actionParams": {"$ref": "#/definitions/CreateTrafficMirroringParams"}
    }
}
