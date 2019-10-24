from cloudshell.cp.core.models import TrafficMirroringResult


class TrafficMirrorFulfillment(object):
    def __init__(self, action, reservation):
        """
        :param cloudshell.cp.core.models.CreateTrafficMirroring action:
        :return:
        """
        self.reservation = reservation
        self.traffic_mirror_filter_id = None
        self.action_id = action.actionId
        self.target_nic_id = action.actionParams.targetNicId
        self.traffic_mirror_target_id = None
        self.source_nic_id = action.actionParams.sourceNicId
        self.session_number = action.actionParams.sessionNumber
        self.session_name = self._get_mirror_session_name()
        self.mirror_session_id = None
        self.filter_rules = action.actionParams.filterRules

    def _get_mirror_session_name(self):
        """
        :param TrafficMirrorFulfillment fulfillment:
        :return:
        """
        return '{2}_{0}_{1}'.format(self.source_nic_id, self.target_nic_id, self.session_number)


def create_results(success, fulfillments, message):
        return [
            TrafficMirroringResult(
                actionId=f.action_id,
                success=success,
                infoMessage=message,
                errorMessage=message,
                sessionId=f.mirror_session_id or '')
            for f in fulfillments]
