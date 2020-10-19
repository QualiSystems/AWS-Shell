import copy
import logging
import uuid

from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.waiters.ami import AMIWaiter

NAME_TAG_KEY = 'Name'


class SnapshotOperation(object):

    def __init__(self, instance_service, image_waiter):
        """
        :param InstanceService instance_service:
        :param AMIWaiter image_waiter
        """
        self.instance_service = instance_service
        self.image_waiter = image_waiter

    def save(self, logger, ec2_session, instance_id, deployed_app_name, snapshot_prefix, no_reboot):
        """
        :param logging.Logger logger:
        :param str snapshot_prefix:
        :param str deployed_app_name:
        :param ec2_session:
        :param str instance_id:
        :param bool no_reboot:
        :return:
        """
        # get instance
        instance = self.instance_service.get_instance_by_id(ec2_session, instance_id)

        if not no_reboot:
            pass  # todo - stop instance and change live status icon

        image_name = "{}-{}".format(deployed_app_name, uuid.uuid4().hex[:8])
        # image_name = uuid.uuid4().hex[:8]

        # save image from instance
        image = instance.create_image(Name=image_name)

        # prepare tags from the original image
        image_tags = self._prepare_tags(instance, image_name, deployed_app_name)
        image.create_tags(Tags=image_tags)

        # wait for the image to be ready
        logger.info("Waiting for the image to be ready")
        self.image_waiter.wait(image, AMIWaiter.AVAILABLE)

        logger.info("Create image from deployed app '{}'. New image id: '{}'"
                    .format(deployed_app_name, image.id))

        return image.id

    def _prepare_tags(self, instance, image_name, deployed_app_name):
        image_tags = copy.deepcopy(instance.tags)
        for tag in image_tags:
            tag['Key'] = self._format_source_key_name(tag['Key'])

        if deployed_app_name:
            image_tags.append({'Key': 'DeployedAppName', 'Value': deployed_app_name})

        image_tags.append({'Key': 'Name', 'Value': image_name})
        image_tags.append({'Key': 'Name', 'Value': image_name})

        return image_tags

    def _format_source_key_name(self, key):
        return 'source.' + key

    def get_image(self, ec2_client, reservation_id, deployed_app_name):
        response = ec2_client.describe_images(Filters=[{'Name': 'tag:' + self._format_source_key_name(NAME_TAG_KEY),
                                                        'Values': [deployed_app_name]}])

        result = []
        for image in response['Images']:
            result.append("Image Name: '{}', Image ID: '{}'".format(image['Name'], image['ImageId']))

        return '\n'.join(result)

    def get_snapshots(self, ec2_session, instance_id, snapshot_name=None):
        instance_id_filter = {'Name': 'tag:InstanceId', 'Values': [instance_id]}
        instance_snapshots = [x for x in ec2_session.snapshots.filter(Filters=[instance_id_filter])]
        result = []
        for snapshot in instance_snapshots:
            for tag in snapshot.tags:
                key = tag.get('Key')
                value = tag.get('Value')
                if key == "Name" and value:
                    if snapshot_name and snapshot_name == value:
                        return snapshot
                    else:
                        result.append(value)

    def restore_snapshot(self, ec2_client, ec2_session, instance_id, snapshot_name, tags):
        instance = self.instance_service.get_instance_by_id(ec2_session, instance_id)
        instance_snapshot = self.get_snapshots(ec2_session=ec2_session,
                                               instance_id=instance_id,
                                               snapshot_name=snapshot_name)
        root_device_mapping = instance.block_device_mappings[0]["DeviceName"]
        root_device_volume_id = instance.block_device_mappings[0]["Ebs"]["VolumeId"]
        instance_root_volume = ec2_session.Volume(root_device_volume_id)

        # Save the instances current state and stop it if necessary.
        current_instance_state = instance.state["Name"]
        instance.stop()
        instance.wait_until_stopped()

        # Detach the volume from the instance and wait for it to become available
        instance_root_volume.detach_from_instance()
        volume_waiter = ec2_client.get_waiter('volume_available')
        volume_waiter.wait(VolumeIds=[instance_root_volume.id])

        # Create a new volume from the requested snapshot and put it in the same availability zone
        # as the current volume then wait for it to finish creating
        volume_create_response = ec2_client.create_volume(AvailabilityZone=instance.placement["AvailabilityZone"],
                                                          SnapshotId=instance_snapshot.id,
                                                          VolumeType=instance_root_volume.volume_type)
        new_volume = ec2_session.Volume(volume_create_response["VolumeId"])
        volume_waiter.wait(VolumeIds=[new_volume.id])

        # Tag the new Volume
        tags.append({'Key': "InstanceId", 'Value': instance_id})
        ec2_session.create_tags(tags)

        # Attach the new Volume to the instance and delete the old volume
        new_volume.attach_to_instance(InstanceId=instance.id, Device=root_device_mapping)
        volume_waiter = ec2_client.get_waiter('volume_in_use')
        volume_waiter.wait(VolumeIds=[new_volume.id])
        instance_root_volume.delete()

        # if the original instance state was Powered On, return it to this state.
        if current_instance_state == "running":
            instance.start()
            instance.wait_until_running()
            instance_ok_waiter = ec2_client.get_waiter('instance_status_ok')
            instance_ok_waiter.wait(InstanceIds=[instance.id])

    def save_snapshot(self, ec2_client, ec2_session, instance_id, snapshot_name, tags):
        instance = self.instance_service.get_instance_by_id(ec2_session, instance_id)
        root_device_volume_id = instance.block_device_mappings[0]["Ebs"]["VolumeId"]
        # {'Key': key, 'Value': value}
        tags.append({"Key": "InstanceId", "Value": str(instance_id)})

        # Snapshot the Volume
        create_snapshot_result = ec2_client.create_snapshot(VolumeId=root_device_volume_id)

        # Wait for the snapshot to finish being created
        snapshot = ec2_session.Snapshot(create_snapshot_result["SnapshotId"])
        snapshot.create_tags(tags)
        snapshot.wait_until_completed()

        return snapshot
