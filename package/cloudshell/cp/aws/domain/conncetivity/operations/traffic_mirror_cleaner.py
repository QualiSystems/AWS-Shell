from botocore.waiter import WaiterModel, create_waiter_with_client


class TrafficMirrorCleaner(object):
    @staticmethod
    def rollback(ec2_client, fulfillments, logger, cloudshell, reservation, session_number_service):
        """
        :param cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services.SessionNumberService session_number_service:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param Logging.Logger logger:
        :type ec2_client: ec2 client
        :param list[cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment] fulfillments:
        :return:
        """

        # note - order matters, i.e. must delete session, before deleting filter, and must delete both to delete target

        mirror_session_ids = [f.mirror_session_id for f in fulfillments if f.mirror_session_id]
        mirror_filter_ids = [f.traffic_mirror_filter_id for f in fulfillments if f.traffic_mirror_filter_id]
        mirror_target_ids = [f.traffic_mirror_target_id for f in fulfillments if f.traffic_mirror_target_id]
        session_numbers = [f.session_number for f in fulfillments if f.session_number]
        session_number_service.release(cloudshell, logger, reservation, session_numbers)

        for f in fulfillments:
            logger.warning('Initiating rollback for traffic mirror request: {0}\n'
                           'session id: {1}\n'
                           'filter id: {2}\n'
                           'target id: {3}'.format(
                f.action_id, f.mirror_session_id, f.traffic_mirror_filter_id, f.traffic_mirror_target_id))

        try:
            TrafficMirrorCleaner.cleanup(ec2_client, mirror_session_ids, mirror_filter_ids, mirror_target_ids)
        except:
            logger.exception('Rollback failed')

    @staticmethod
    def cleanup(ec2_client, traffic_mirror_session_ids=None, traffic_mirror_filter_ids=None,
                traffic_mirror_target_ids=None):
        """
        :param list[str] traffic_mirror_session_ids:
        :param list[str] traffic_mirror_filter_ids:
        :param list[str] traffic_mirror_target_ids:
        """
        TrafficMirrorCleaner.delete_mirror_sessions(ec2_client, traffic_mirror_session_ids)
        TrafficMirrorCleaner.delete_mirror_filters(ec2_client, traffic_mirror_filter_ids)
        TrafficMirrorCleaner.delete_mirror_targets(ec2_client, traffic_mirror_target_ids)

    @staticmethod
    def _create_delete_traffic_session_waiter(ec2_client):
        delete_session_model = WaiterModel({
            "version": 2,
            "waiters": {
                "TrafficMirrorDeleted": {
                    "delay": 15,
                    "operation": "DescribeTrafficMirrorSessions",
                    "maxAttempts": 40,
                    "acceptors": [
                        {
                            "matcher": "error",
                            "expected": "InvalidTrafficMirrorSessionId.NotFound",
                            "state": "success"
                        }
                    ]}}}
        )
        delete_session_waiter = create_waiter_with_client('TrafficMirrorDeleted',
                                                          delete_session_model,
                                                          ec2_client)
        return delete_session_waiter

    @staticmethod
    def _create_traffic_mirror_filter_delete_waiter(ec2_client):
        delete_filter_waiter_model = WaiterModel({
            "version": 2,
            "waiters": {
                "TrafficMirrorFiltersDeleted": {
                    "delay": 15,
                    "operation": "DescribeTrafficMirrorFilters",
                    "maxAttempts": 40,
                    "acceptors": [
                        {
                            "matcher": "error",
                            "expected": "InvalidTrafficMirrorFilterId.NotFound",
                            "state": "success"
                        }
                    ]}}}
        )
        traffic_mirror_filter_deleted_waiter = create_waiter_with_client('TrafficMirrorFiltersDeleted',
                                                                         delete_filter_waiter_model,
                                                                         ec2_client)
        return traffic_mirror_filter_deleted_waiter

    @staticmethod
    def _create_traffic_mirror_target_delete_waiter(ec2_client):
        delete_target_waiter_model = WaiterModel({
            "version": 2,
            "waiters": {
                "TrafficMirrorTargetsDeleted": {
                    "delay": 15,
                    "operation": "DescribeTrafficMirrorTargets",
                    "maxAttempts": 40,
                    "acceptors": [
                        {
                            "matcher": "error",
                            "expected": "InvalidTrafficMirrorTargetId.NotFound",
                            "state": "success"
                        }
                    ]}}}
        )
        traffic_mirror_filter_deleted_waiter = create_waiter_with_client('TrafficMirrorTargetsDeleted',
                                                                         delete_target_waiter_model,
                                                                         ec2_client)
        return traffic_mirror_filter_deleted_waiter

    @staticmethod
    def get_traffic_mirror_filters_by_reservation_id(ec2_client, reservation_id):
        traffic_mirror_filters = []
        response = ec2_client.describe_traffic_mirror_filters(
            Filters=[
                {
                    'Name': 'tag:ReservationId',
                    'Values': [
                        str(reservation_id)
                    ]
                },
            ],
            MaxResults=123,
            NextToken='string'
        )
        traffic_mirror_filters.extend(response['TrafficMirrorFilters'])
        while 'NextToken' in response:
            response = ec2_client.describe_traffic_mirror_filters(NextToken=response['NextToken'])
            traffic_mirror_filters.extend(response['TrafficMirrorFilters'])

        return traffic_mirror_filters

    @staticmethod
    def try_delete_mirror_session(ec2_client, mirror_session_id):
        if mirror_session_id:
            delete_session_waiter = TrafficMirrorCleaner._create_delete_traffic_session_waiter(ec2_client)
            ec2_client.delete_traffic_mirror_session(TrafficMirrorSessionId=mirror_session_id)
            delete_session_waiter.wait(TrafficMirrorSessionIds=[mirror_session_id])

    @staticmethod
    def delete_mirror_sessions(ec2_client, mirror_session_ids=None):
        if mirror_session_ids:
            delete_session_waiter = TrafficMirrorCleaner._create_delete_traffic_session_waiter(ec2_client)
            for id in mirror_session_ids:
                ec2_client.delete_traffic_mirror_session(TrafficMirrorSessionId=id)
            delete_session_waiter.wait(TrafficMirrorSessionIds=mirror_session_ids)

    @staticmethod
    def delete_mirror_filters(ec2_client, mirror_filter_ids=None):
        if mirror_filter_ids:
            delete_filter_waiter = TrafficMirrorCleaner._create_traffic_mirror_filter_delete_waiter(ec2_client)
            for id in mirror_filter_ids:
                ec2_client.delete_traffic_mirror_filter(TrafficMirrorFilterId=id)
            delete_filter_waiter.wait(TrafficMirrorFilterIds=mirror_filter_ids)

    @staticmethod
    def delete_mirror_targets(ec2_client, mirror_target_ids=None):
        if mirror_target_ids:
            delete_target_waiter = TrafficMirrorCleaner._create_traffic_mirror_target_delete_waiter(ec2_client)
            for id in mirror_target_ids:
                ec2_client.delete_traffic_mirror_target(TrafficMirrorTargetId=id)
            delete_target_waiter.wait(TrafficMirrorTargetIds=mirror_target_ids)

    @staticmethod
    def try_delete_mirror_filter(ec2_client, traffic_mirror_filter_id):
        if traffic_mirror_filter_id:
            delete_filter_waiter = TrafficMirrorCleaner._create_traffic_mirror_filter_delete_waiter(ec2_client)
            ec2_client.delete_traffic_mirror_filter(TrafficMirrorFilterId=traffic_mirror_filter_id)
            delete_filter_waiter.wait(TrafficMirrorFilterIds=[traffic_mirror_filter_id])

    @staticmethod
    def try_delete_mirror_target(ec2_client, traffic_mirror_target_id):
        if traffic_mirror_target_id:
            ec2_client.delete_traffic_mirror_target(TrafficMirrorTargetId=traffic_mirror_target_id)
