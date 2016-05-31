import uuid


class SecurityGroupService(object, ):
    @staticmethod
    def delete_security_group(security_group):
        try:
            security_group.delete()
        except Exception:
            raise

    def delete_all_security_groups_of_instance(self, instance):
        for security_group in instance.security_groups:
            self.delete_security_group(security_group)
