from jsonpickle import json


class SessionNumberService(object):
    OWNER_ID = 'trafficmirrorsessionnumber'

    def release(self, cloudshell, logger, reservation, session_numbers, pool_id):
        """
        :param str pool_id:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param logging.Logger logger:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param list(str) session_numbers:
        """

        try:
            logger.info('Releasing from poolId {0} in reservationId {1} session numbers {2}'.format(pool_id,
                                                                                                    reservation.reservation_id,
                                                                                                    repr(session_numbers)))
            cloudshell.ReleaseFromPool(values=session_numbers,
                                       poolId=pool_id,
                                       ownerId=self.OWNER_ID,
                                       reservationId=reservation.reservation_id)
        except Exception as e:
            if 'reservation has ended' in e.message:
                raise Exception('Tried to checkout a session number for traffic mirroring, but reservation has already ended')
            logger.exception('Could not release session number: ' + e.message)

    def checkout(self, cloudshell, logger, reservation, source_nic, specific_number=None):
        """
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param logging.Logger logger:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param str source_nic:
        :param str specific_number:
        :return:
        """
        selection_criteria = self._get_selection_criteria(source_nic, reservation.reservation_id, specific_number)

        try:
            result = cloudshell.CheckoutFromPool(selection_criteria)
            return result.Items[0]

        except Exception as e:
            if 'reservation has ended' in e.message:
                raise Exception('Tried to checkout a session number for traffic mirroring, but reservation has already ended')
            else:
                logger.error(unavailable_msg(source_nic, reservation.reservation_id))
                logger.error(e.message)
                raise Exception(unavailable_msg(source_nic, reservation.reservation_id))

    @staticmethod
    def _get_selection_criteria(source_nic, reservation_id, specific_number=None):
        request = {
            'isolation': 'Exclusive',
            'reservationId': reservation_id,
            'poolId': source_nic,  # The session number determines the order that traffic mirror sessions are evaluated when an interface is used by multiple sessions that have the same interface, but have different traffic mirror targets and traffic mirror filters. Traffic is only mirrored one time.
            'ownerId': SessionNumberService.OWNER_ID
        }

        if not specific_number:
            request['type'] = 'NextAvailableNumericFromRange'
            request['requestedRange'] = {'Start': 1, 'End': 32766}
        else:
            request['type'] = 'SpecificNumeric'
            request['requestedItem'] = {'Value': specific_number}

        selection_criteria = json.dumps(request)
        return selection_criteria


UNAVAILABLE_MSG = 'Was not able to find an available session number for {0}.\n' \
                  'Please note that session number must be between 1-32766 and unique for a particular source NIC.\n' \
                  'To learn more, please see documentation at ' \
                  'https://docs.aws.amazon.com/vpc/latest/mirroring/traffic-mirroring-session.html' \
                  '\nPlease also check logs at %PROGRAMDATA%\\QualiSystems\\logs\\{1} for additional information.'


def unavailable_msg(source_nic, reservation_id):
    return UNAVAILABLE_MSG.format(source_nic, reservation_id)