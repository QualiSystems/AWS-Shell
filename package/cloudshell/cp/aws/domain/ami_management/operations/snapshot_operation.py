import copy
import logging

from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter

NAME_TAG_KEY = 'Name'


class SnapshotOperation(object):

    def __init__(self, instance_service, image_waiter):
        """
        :param InstanceService instance_service:
        :param SubnetWaiter image_waiter
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

        image_name = "{}{}".format(snapshot_prefix, deployed_app_name)

        # save image from instance
        image = instance.create_image(Name=image_name)

        # prepare tags from the original image
        image_tags = self._prepare_tags(instance, image_name, snapshot_prefix)
        image.create_tags(Tags=image_tags)

        # wait for the image to be ready
        logger.info("Waiting for the image to be ready")
        self.image_waiter.wait(image, SubnetWaiter.AVAILABLE)

        logger.info("Create image from deployed app '{}'. New image id: '{}'"
                    .format(deployed_app_name, image.id))

        return image_name, image.id

    def _prepare_tags(self, instance, image_name, snapshot_prefix):
        image_tags = copy.deepcopy(instance.tags)
        for tag in image_tags:
            tag['Key'] = self._format_source_key_name(tag['Key'])

        if snapshot_prefix:
            image_tags.append({'Key': 'SnapshotPrefix', 'Value': snapshot_prefix})

        image_tags.append({'Key': 'Name', 'Value': image_name})

        return image_tags

    def _format_source_key_name(self, key):
        return 'source.' + key

    def get(self, ec2_client, reservation_id, deployed_app_name):
        response = ec2_client.describe_images(Filters=[{'Name': 'tag:' + self._format_source_key_name(NAME_TAG_KEY),
                                                        'Values': [deployed_app_name]}])

        result = []
        for image in response['Images']:
            result.append("Image Name: '{}', Image ID: '{}'".format(image['Name'], image['ImageId']))

        return '\n'.join(result)

