import itertools
import threading
from collections import defaultdict

import time

from cloudshell.cp.aws.domain.conncetivity.operations.traffic_mirror_cleaner import TrafficMirrorCleaner
from cloudshell.cp.aws.models.traffic_mirror_fulfillment import TrafficMirrorFulfillment, CreateResult

flatten = itertools.chain.from_iterable


class CheckCancellationThread(threading.Thread):
    def __init__(self, cancellation_context, cancellation_service):
        super(CheckCancellationThread, self).__init__()
        self._stop = threading.Event()
        self.cancellation_context = cancellation_context
        self.cancellation_service = cancellation_service

    def run(self):
        while True:
            if self.stopped():
                return
            time.sleep(1)
            cancelled = self.cancellation_service.check_if_cancelled(self.cancellation_context)
            if cancelled:
                raise Exception('User cancelled traffic mirroring')

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class CreateTrafficMirrorOperation(object):
    def __init__(self, tag_service, session_number_service, traffic_mirror_service, cancellation_service):
        """
        :param cloudshell.cp.aws.domain.common.cancellation_service.CommandCancellationService cancellation_service: object
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        :param cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services.SessionNumberService session_number_service:
        """
        self._tag_service = tag_service
        self._session_number_service = session_number_service
        self._traffic_mirror_service = traffic_mirror_service
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
        :param logger:
        :return:
        """

        logger.info('Received request to deploy traffic mirroring. Here are the params:\n' + '\n'
                    .join(str(x) for x in actions))

        self._validate_actions(actions, logger)
        self._checkout_session_numbers(actions, cloudshell, logger, reservation)

        target_nics_to_fulfillments = self._convert_traffic_requests_to_fulfillments(actions, reservation)
        target_nics = target_nics_to_fulfillments.keys()
        fulfillments = list(flatten(target_nics_to_fulfillments.values()))

        success = False

        try:
            cancel_checker = CheckCancellationThread(cancellation_context, self._cancellation_service)
            cancel_checker.start()
            self._get_or_create_targets(ec2_client, reservation, target_nics, target_nics_to_fulfillments)
            self._get_or_create_sessions(ec2_client, fulfillments)
            cancel_checker.stop()

            success = True
            message = 'Success'

        except Exception as e:
            message = e.message
            TrafficMirrorCleaner.rollback(ec2_client, fulfillments, logger)

        result = CreateResult(success, fulfillments, message)
        return result

    def _get_or_create_targets(self, ec2_client, reservation, target_nics, target_nics_to_fulfillments):
        targets_found_nics_to_target_id = self._traffic_mirror_service.find_traffic_targets_by_nics(ec2_client,
                                                                                                    target_nics)
        self._create_targets_or_assign_existing_targets(ec2_client,
                                                        target_nics_to_fulfillments,
                                                        targets_found_nics_to_target_id,
                                                        self._tag_service,
                                                        reservation)

    def _get_or_create_sessions(self, ec2_client, fulfillments):
        session_name_to_fulfillment = {f.session_name: f for f in fulfillments}
        session_name_to_found_session = self._traffic_mirror_service.find_sessions_by_session_names(ec2_client, session_name_to_fulfillment.keys())
        for s in session_name_to_fulfillment.keys():
            fulfillment = session_name_to_fulfillment[s]
            if s not in session_name_to_found_session.keys():
                fulfillment.mirror_session_id = self._create_session(ec2_client, fulfillment)
            else:
                fulfillment.mirror_session_id = session_name_to_found_session[s]['TrafficMirrorSessionId']

    def _create_targets_or_assign_existing_targets(self, ec2_client,
                                                   target_nics_to_fulfillments,
                                                   nics_to_found_target_ids,
                                                   tag_service,
                                                   reservation):
        """
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        """
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
    def _convert_traffic_requests_to_fulfillments(actions, reservation):
        target_nics_to_fulfillments = defaultdict(list)
        [target_nics_to_fulfillments[x.actionParams.targetNicId].append(TrafficMirrorFulfillment(x, reservation))
         for x in actions]
        return target_nics_to_fulfillments

    @staticmethod
    def _assign_target_to_fulfillments(fulfillments, traffic_target_id):
        for fulfillment in fulfillments:
            fulfillment.traffic_mirror_target_id = traffic_target_id

    def _create_session(self, ec2_client, fulfillment):
        """
        :param cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment fulfillment:
        """
        traffic_filter_tags = self._tag_service.get_default_tags('filter-' + fulfillment.session_name,
                                                                 fulfillment.reservation)

        mirror_session_tags = self._tag_service.get_default_tags('session-' + fulfillment.session_name,
                                                                 fulfillment.reservation)

        fulfillment.traffic_mirror_filter_id = \
            self._traffic_mirror_service.create_filter(ec2_client, traffic_filter_tags)

        self._traffic_mirror_service.create_filter_rules(ec2_client, fulfillment)

        return self._traffic_mirror_service.create_traffic_mirror_session(ec2_client, fulfillment, mirror_session_tags)

    def _validate_actions(self, actions, logger):
        self._session_numbers_are_valid(actions, logger)  # must be 1-32766 or NONE

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
                a.actionParams.sessionNumber = None
