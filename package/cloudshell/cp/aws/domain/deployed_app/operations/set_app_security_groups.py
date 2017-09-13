class SetAppSecurityGroupsOperation(object):
    def __init__(self):
        """
        :return:
        """

    def set_app_security_groups(self, app_security_group_model):
        """
        Set custom security groups to a deployed app
        :param AppSecurityGroupModel app_security_group_model:
        :return:
        """

        """
        - get vm id from deployed app details
        - for each security_groups_configuration
        - - get subnet id
        - - get nic (s) !!!
            for each nic !!!
                - - if custom security group exists --> overwrite it
                - - if custom security group doesn't exist
                - - - create a new security group
                - - - attach it to the nic
                - - - add (from input) rules to the security group
                - - - go to the next nic
        
        """

        # app_security_group_model
