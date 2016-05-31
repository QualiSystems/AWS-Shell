class TagManagerService(object):
    @staticmethod
    def set_ami_instance_tag(ec2_session, instance, tags):
        return ec2_session.create_tags(Resources=[instance.id], Tags=tags)

    @staticmethod
    def set_security_group_tags(security_group, name):
        return security_group.create_tags(Tags=TagManagerService.get_default_tags(name))

    @staticmethod
    def get_default_tags(name):
        return [TagManagerService._get_kvp("Name", name),
                TagManagerService._get_created_by_kvp()]

    @staticmethod
    def _get_created_by_kvp():
        return TagManagerService._get_kvp('CreatedBy', 'Quali')

    @staticmethod
    def _get_kvp(key, value):
        return {'Key': key, 'Value': value}