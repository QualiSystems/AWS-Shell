import binascii
from base64 import b64decode

from Crypto.PublicKey import RSA

from cloudshell.cp.aws.models.ami_credentials import AMICredentials


class InstanceCredentialsService(object):
    DEFAULT_USER_NAME = "Administrator"

    def __init__(self, password_waiter):
        self.password_waiter = password_waiter

    def get_windows_credentials(self, instance, key_value, wait_for_password=True):
        """

        :param instance: Ami amazon instance
        :param key_value: pem lines
        :type key_value: str
        :param wait_for_password:
        :type wait_for_password: bool
        :return:
        :rtype: AMICredentials
        """
        password_data = instance.password_data()['PasswordData']
        if not password_data and wait_for_password:
            password_data = self.password_waiter.wait(instance)

        if not password_data:
            return None

        return AMICredentials(user_name=self.DEFAULT_USER_NAME,
                              password=self.decrypt_password(key_value, password_data))

    def decrypt_password(self, key_value, encrypted_data):
        rsa_key = RSA.importKey(key_value)
        encrypted_data = b64decode(encrypted_data)
        cipher_text = int(binascii.hexlify(encrypted_data), 16)

        # Decrypt it
        plaintext = rsa_key.decrypt(cipher_text)

        # This is the annoying part.  long -> byte array
        decrypted_data = self._long_to_bytes(plaintext)
        # Now Unpad it
        return self._pkcs1_unpad(decrypted_data)

    @staticmethod
    def _pkcs1_unpad(text):
        # From http://kfalck.net/2011/03/07/decoding-pkcs1-padding-in-python
        if len(text) > 0 and text[0] == '\x02':
            # Find end of padding marked by nul
            pos = text.find('\x00')
            if pos > 0:
                return text[pos + 1:]
        return None

    @staticmethod
    def _long_to_bytes(val, endianness='big'):
        # From http://stackoverflow.com/questions/8730927/convert-python-long-int-to-fixed-size-byte-array
        # one (1) hex digit per four (4) bits
        try:
            # Python < 2.7 doesn't have bit_length =(
            width = val.bit_length()
        except:
            width = len(val.__hex__()[2:-1]) * 4
        # unhexlify wants an even multiple of eight (8) bits, but we don't
        # want more digits than we need (hence the ternary-ish 'or')
        width += 8 - ((width % 8) or 8)
        # format width specifier: four (4) bits per hex digit
        fmt = '%%0%dx' % (width // 4)
        # prepend zero (0) to the width, to zero-pad the output
        s = binascii.unhexlify(fmt % val)
        if endianness == 'little':
            # see http://stackoverflow.com/a/931095/309233
            s = s[::-1]
        return s
