

class EC2StorageService(object):
    @staticmethod
    def get_available_volumes(ec2_session):
        available_volumes = ec2_session.volumes.filter(
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
        return available_volumes

    @staticmethod
    def delete_volume(volume):
        volume.delete()

    def get_instance_available_volumes(self, ec2_session, instance_id):
        volumes = [v for v in self.get_available_volumes(ec2_session)
                   if v.attach_data.instance_id == instance_id]
        return volumes

    def delete_all_instance_volumes(self, ec2_session, instance_id):
        volumes = self.get_instance_available_volumes(ec2_session, instance_id)
        for volume in volumes:
            self.delete_volume(volume)
        return