from unittest import TestCase

from mock import MagicMock, patch

from cloudshell.cp.aws.domain.services.ami_credentials_service.key_pair_loader import KeyPairProvider


class TestKeyPairLoader(TestCase):
    def test_load(self):
        self.ket_pair_loader = KeyPairProvider()
        with patch('cloudshell.cp.aws.domain.services.ami_credentials_service.key_pair_loader.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=file)
            self.ket_pair_loader.load('zz', 'aa', self.ket_pair_loader.FILE_SYSTEM)

    def test_load_validation(self):
        self.ket_pair_loader = KeyPairProvider()

        self.assertRaises(ValueError, self.ket_pair_loader.load, None, 'aa', self.ket_pair_loader.FILE_SYSTEM)
        self.assertRaises(ValueError, self.ket_pair_loader.load, 'aa', None, self.ket_pair_loader.FILE_SYSTEM)
        self.assertRaises(ValueError, self.ket_pair_loader.load, 'aa', 'aa', None)
