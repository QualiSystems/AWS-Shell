class TagNames(object):
    CreatedBy = 'CreatedBy'
    ReservationId = 'ReservationId'
    Name = 'Name'
    Isolation = 'Isolation'


class IsolationTagValues(object):
    Exclusive = 'Exclusive'
    Shared = 'Shared'


class TagService(object):
    CREATED_BY_QUALI = "Quali"

    def __init__(self):
        pass

    def get_security_group_tags(self, name, isolation, reservation_id):
        """
        returns the default tags with the isolation tag
        :param str name: the name of the resource
        :param str isolation: the isolation level of the resource
        :param str reservation_id: reservation id
        :return: list[dict]
        """
        tags = self.get_default_tags(name, reservation_id)
        tags.append(self._get_kvp(TagNames.Isolation, isolation))
        return tags

    def get_default_tags(self, name, reservation_id):
        """
        returns the default tags of a resource. Name,reservationId,createdBy
        :param str name: the name of the resource
        :param str reservation_id: reservation id
        :return: list[dict]
        """
        return [self._get_kvp(TagNames.Name, name),
                self.get_created_by_kvp(),
                self.get_reservation_tag(reservation_id)]

    def get_reservation_tag(self, reservation_id):
        return self._get_kvp(TagNames.ReservationId, reservation_id)

    @staticmethod
    def set_ec2_resource_tags(resource, tags):
        """
        Will set tags on a EC2 resource
        :param resource: EC2 resource
        :param tags: Array of key pair tags
        :type tags: list[dict]
        :return:
        """
        resource.create_tags(Tags=tags)

    def get_created_by_kvp(self):
        return self._get_kvp(TagNames.CreatedBy, TagService.CREATED_BY_QUALI)

    @staticmethod
    def _get_kvp(key, value):
        return {'Key': key, 'Value': value}
