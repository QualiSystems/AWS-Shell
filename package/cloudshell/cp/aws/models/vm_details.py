class VmDetailsRequest(object):
    def __init__(self, item):
        self.uuid = item.deployedAppJson.vmdetails.uid
        self.app_name = item.deployedAppJson.name