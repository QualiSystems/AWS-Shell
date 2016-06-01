from enum import Enum


class TagNames(object):
    CreatedBy = 'CreatedBy'
    ReservationId = 'ReservationId'
    Name = 'Name'
    Isolation = 'Isolation'


class IsolationEnum(Enum):
    exclusive = 1
    shared = 2


class TagCreatorService(object):
    CreatedByTagValue = "Quali"

    def __init__(self):
        pass

    def get_security_group_tags(self, name, isolation, reservation_id):
        """
        returns the default tags with the isolation tag
        :param str name: the name of the resource
        :param IsolationEnum isolation: the isolation level of the resource
        :param str reservation_id: reservation id
        :return: list[dict]
        """
        tags = self.get_default_tags(name, reservation_id)
        tags.append(self._get_kvp(TagNames.Isolation, isolation.name))
        return tags

    def get_default_tags(self, name, reservation_id):
        """
        returns the default tags of a resource. Name,reservationId,createdBy
        :param str name: the name of the resource
        :param str reservation_id: reservation id
        :return: list[dict]
        """
        return [self._get_kvp(TagNames.Name, name), self._get_created_by_kvp(),
                self._get_kvp(TagNames.ReservationId, reservation_id)]

    def _get_created_by_kvp(self):
        return self._get_kvp(TagNames.CreatedBy, TagCreatorService.CreatedByTagValue)

    def _get_kvp(self, key, value):
        return {'Key': key, 'Value': value}
