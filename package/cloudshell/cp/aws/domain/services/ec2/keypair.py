RESERVATION_KEY_PAIR = 'reservation key pair {0}'
KEY_FORMAT = 'reservation-id-{0}/{1}.pem'


class KeyPairService(object):
    def __init__(self, s3_service):
        """
        :param s3_service: s3 service
        :type s3_service: cloudshell.cp.aws.domain.services.s3.bucket.S3BucketService
        """
        self.s3_service = s3_service

    def get_key_pair_by_name(self, s3_session, bucket_name, reservation_id):
        """
        Will load a key form s3 if exists
        :param s3_session: s3 session
        :param bucket_name: The bucket name
        :type bucket_name: str
        :param reservation_id: Reservation Id
        :type reservation_id: str
        :return:
        """
        s3_key = self._get_s3_key_location(reservation_id)
        s3_obj = self.s3_service.get_key(s3_session, bucket_name, s3_key)
        return self.s3_service.get_body_of_object(s3_obj)

    def create_key_pair(self, ec2_session, s3_session, bucket, reservation_id):
        key_pair = ec2_session.create_key_pair(KeyName=self._get_reservation_key_name(reservation_id))
        self._save_key_to_s3(bucket, key_pair, reservation_id, s3_session)
        return key_pair

    def _save_key_to_s3(self, bucket, key_pair, reservation_id, s3_session):
        s3_key = self._get_s3_key_location(reservation_id)
        self.s3_service.put_key(s3_session, bucket_name=bucket, key=s3_key, value=key_pair.key_material)

    def _get_s3_key_location(self, reservation_id):
        return KEY_FORMAT.format(reservation_id, self._get_reservation_key_name(reservation_id))

    @staticmethod
    def _get_reservation_key_name(reservation_id):
        return RESERVATION_KEY_PAIR.format(reservation_id)
