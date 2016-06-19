import botocore


class KeyPairService(object):
    def __init__(self):
        pass

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
        try:
            obj = \
                s3_session.Object(bucket_name, s3_key)
            obj.load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return None
            else:
                raise e
        return obj

    def _get_s3_key_location(self, reservation_id):
        return 'reservation-id-{0}/{1}.pem'.format(reservation_id, self._get_reservation_key_name(reservation_id))

    def create_key_pair(self, ec2_session, s3_session, bucket, reservation_id):
        key_pair = ec2_session.create_key_pair(KeyName=self._get_reservation_key_name(reservation_id))
        self._save_key_to_s3(bucket, key_pair, reservation_id, s3_session)
        return key_pair

    def _save_key_to_s3(self, bucket, key_pair, reservation_id, s3_session):
        s3_key = self._get_s3_key_location(reservation_id)
        bytes_arr = key_pair.key_material.encode('utf-8')
        s3_session.Bucket(bucket).put_object(Body=bytes_arr, Key=s3_key)

    def _get_reservation_key_name(self, reservation_id):
        return 'reservation key pair {0}'.format(reservation_id)
