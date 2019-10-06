from botocore.waiter import WaiterModel, create_waiter_with_client


class TrafficMirrorCleaner(object):
    @staticmethod
    def rollback(ec2_client, fulfillments):
        """
        :type ec2_client: ec2 client
        :param list[TrafficMirrorFulfillment] fulfillments:
        :return:
        """
        delete_session_waiter = TrafficMirrorCleaner._create_delete_traffic_session_waiter(ec2_client)

        # note - order matters, i.e. must delete session, before deleting filter, and must delete both to delete target
        for f in fulfillments:
            TrafficMirrorCleaner.try_delete_mirror_session(ec2_client, f.mirror_session_id)
            delete_session_waiter.wait(TrafficMirrorSessionIds=[f.mirror_session_id])
            TrafficMirrorCleaner.try_delete_mirror_filter(ec2_client, f.traffic_mirror_filter_id)
            TrafficMirrorCleaner.try_delete_mirror_target(ec2_client, f.traffic_mirror_target_id)

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
    def try_delete_mirror_session(ec2_client, mirror_session_id):
        if mirror_session_id:
            ec2_client.delete_traffic_mirror_session(TrafficMirrorSessionId=mirror_session_id)

    @staticmethod
    def try_delete_mirror_filter(ec2_client, traffic_mirror_filter_id):
        if traffic_mirror_filter_id:
            ec2_client.delete_traffic_mirror_filter(TrafficMirrorFilterId=traffic_mirror_filter_id)

    @staticmethod
    def try_delete_mirror_target(ec2_client, traffic_mirror_target_id):
        if traffic_mirror_target_id:
            ec2_client.delete_traffic_mirror_target(TrafficMirrorTargetId=traffic_mirror_target_id)