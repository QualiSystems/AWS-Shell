from cloudshell.cp.core.models import ConnectToSubnetParams


class AbstractDeviceIndexStrategy(object):
    def __init__(self):
        pass

    def apply(self, actions):
        raise Exception


class AllocateMissingValuesDeviceIndexStrategy(AbstractDeviceIndexStrategy):
    def __init__(self):
        AbstractDeviceIndexStrategy.__init__(self)

    def apply(self, actions):
        """
        Allocate device index values to actions with device index and validate all requested device indexes are valid
        :param list[NetworkAction] actions:
        :return:
        """

        # get all SubnetConnection actions
        subnet_conn_actions = filter(lambda x: isinstance(x.actionParams, ConnectToSubnetParams), actions)

        # get all actions with valid device index (>=0)
        specific_device_index_actions = filter(
                lambda x: self._is_vnic_name_valid(x),
                subnet_conn_actions)

        # validate no duplicate device indexes
        if len(set(map(lambda x: x.actionParams.vnicName, specific_device_index_actions))) - \
                len(specific_device_index_actions):
            raise ValueError("Duplicate 'Requested vNic Name' attribute value found")

        # sort by device index
        specific_device_index_actions_sorted = sorted(specific_device_index_actions,
                                                      key=lambda x: x.actionParams.vnicName)

        # get all actions without device index
        no_device_index_actions = list(set(subnet_conn_actions) - set(specific_device_index_actions))

        # allocate device index to actions without device index and add to the sorted list
        for no_di_action in no_device_index_actions:
            device_index_counter = 0
            for di_action in specific_device_index_actions_sorted:
                if di_action.actionParams.vnicName != device_index_counter:
                    no_di_action.actionParams.vnicName = device_index_counter
                    break

                device_index_counter += 1

            if not self._is_vnic_name_valid(no_di_action):
                no_di_action.actionParams.vnicName = device_index_counter

            specific_device_index_actions_sorted.insert(device_index_counter, no_di_action)

        # make sure device index values are continues
        if specific_device_index_actions_sorted[-1].actionParams.vnicName != \
                len(specific_device_index_actions_sorted) - 1:
            raise ValueError("'Requested vNic Name' attribute values are not a continuous list")

    def _is_vnic_name_valid(self, action): #vnicName = device_index(AWS)
        return action.actionParams.vnicName is not None and int(action.actionParams.vnicName) >= 0
