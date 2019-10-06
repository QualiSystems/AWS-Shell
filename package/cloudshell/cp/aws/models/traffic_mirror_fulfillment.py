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
        self.session_number = action.actionParams.sessionNumber  # todo handle empty session number, get next available, etc
        self.session_name = self._get_mirror_session_name()
        self.mirror_session_id = None
        self.filter_rules = action.actionParams.filterRules

    def _get_mirror_session_name(self):
        """
        :param TrafficMirrorFulfillment fulfillment:
        :return:
        """
        return '{2}_{0}_{1}'.format(self.source_nic_id, self.target_nic_id, self.session_number)


class CreateResult(object):
    def __init__(self, success, fulfillments, message):
        self.Success = success
        self.Fulfillments = fulfillments
        self.Message = message