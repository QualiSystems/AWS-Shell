from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.instance_credentials import InstanceCredentialsService
from cloudshell.cp.aws.domain.services.waiters.password import PasswordWaiter


class TestAmiCredentialsService(TestCase):
    def setUp(self):
        self.password_waiter = Mock(spec=PasswordWaiter)
        self.credentials_service = InstanceCredentialsService(self.password_waiter)
        self.pem = ['-----BEGIN RSA PRIVATE KEY-----\n',
                    'MIIEpQIBAAKCAQEAzdX6TR8fnJ0vXilViU5OHzvHfQVXdCufZcr1yDiT3hJ04IgX/INaOfI5+xIC\n', '+qrl9IMJ19Tol/t+asB3eiIo2DK6K5DFYhBDSGKfC2AE+c53B/eeTq/+CGjTma6bNaFSNkiJdOhM\n', 'fNdmAOYYx4B2PqZXgNPGbN3WEGYldU6DiX1IU/hmihjdoW8oL/84DUrkJCl+lZhqP9uVHMp/8yzu\n', 'GovUOF2FNuXMo0tSFeUBeUKZig28u/lhuCEqq2TkHbpvlojjyVqqRoxqw/2ZnUua4PnKSx1U8ddg\n', 'OGg4QXxX1D2DQ8XpRL7pEYdK3A51AaZr7IcpSwtDm5XS/FZ0slCUFwIDAQABAoIBAB3hlGahwAsS\n', 'XpAC3CIEth6epQUnQ1zgAFHctvWMERtJ/qGh4CmOQAjtezFRmhEdwihO5ZzpkaKOpfmFW1LlppxM\n', 'MO6mI6FqzvmxJ3mVROOm72y+q8KslepOnXlP+cQ9WRv8R8gq+P+enXY/8RT1NzU9HLLdC48+XRcg\n', 'XQu8jCfnP1yxKFBxvd8iJtb59KWtaljHoYZSy1P+QPXWtaMb9p+Vd91g9UfPr0b5Ih+Q2AZQP1/F\n', 'I+TypGCEp16K2xIiXaf/CxEWGfRTnwhyyxnEB0apcDv4KJtiZlcl81y3Haeuo6+A8PksnVXDACY3\n', 'GRLksEGIfokb9rqFnk4ay37N1zECgYEA8ggt65yj6iAp1WzspinzxKjQovcUBt1nMo63I1RB41fb\n', 'g0kVHigZDpoqziSZoHmt7mSjS1OBq6xNnmtCOFF4uYkA5d7WyFSfeKSXqT5WFfPOOoGVnw4mIoeD\n', 'OVV401pObis+sVhIYb5nOepDjnV7XIiIlV8DRu8RuP+PKp8C9x0CgYEA2bcH9tJHTqUOs4us0KWO\n', '+5To96iEqqs5bnIZueNGRDGZkSrjX46IGS5o+awCChvvJAPf/CRSpoQhQqcUCy+deNrfQHt2Zpaq\n', 'gD9Qv3AKv5ESnvqnLVFy4FVYvTIDxs8rbTAVHe1/IBi5+xAOnpi2riPhTOVzyJ8NhhwtVYyDbcMC\n', 'gYEA2HcESvOfjmgRwjZXOQ3QXZT2dKoymSkvgQIvPUPAYgpT44lbf8sxDeRIYHJPjD0HmG0dtuMK\n', '2HWUPhmD8ka7iITF7tFsm2ND9WyPz+hWqe+SBLWdEdJfvQYiEQcmtzDPcKzwt0BUDEd0n1Gr9h+Q\n', 'o2PhdGaz0Z9D5Id8jgwFZOkCgYEA0hPg5XPGRsbSRsGyQapfK7dmjQLY8O5DfqUu2cXKWacarY8a\n', '02vvO40i0jf9x89ok/IBQYWzEuZQScZ6esi5RJK99bSsbRVY9GMkAXWViX/s3eazRfFfzcPM2tLV\n', '/hKNrtBEsBopHsl9PBskYDivnZ0Vm2OUs7N2E0BBJlltwI0CgYEA5/eb88pqBcCrfrYi4U8WN3id\n', 'o0t3dj4ca7BPGwvGGMuEB4JPZmsS3AWMGXKSBpEpqMSxHMeTZtxo/ioi4mEGM5SMi0KLSnrWuuYX\n', '+OQfjjQfag6Y7SdiQAyhvpndODqEiqfFDqCnR11T447V/JwyEdxFUwYoLiot5tcZOOOxl2o=\n', '-----END RSA PRIVATE KEY-----']
        self.encrypted = 'NGtKthoEIcRdof+dlQJcJ87HQpPfjwFHKe6e5fiSCt2l523FWgIuqIv+Pda/KF+q/jzhacospZUjQqSBX7aKHA1Qm7tWsNywYP0nAypJOTU0UtJZKVZ9ymXHsPXq+kvaEtq0xvl08MCKUiROlV7jlS1sySvspcum5E49s8lm2nAS9W4dljdytFP/CtEDEfOec87DQG9aCPsDOGbH8efWpEDEQ5pzNhybGyrlI3x8PxFM5JNtSZFTQxCs0vfYjsM2I3VKcrIuVGaQOu9qZZArzANUDCbE3V+BD664y0W5h4RjyowhEAtcTc8NxEFAYOKMJAb253TjLr3Vk/7MmwgFkA=='
        self.decrypted = '542(LhS@Ymq'

    def test_get_windows_credentials_wait(self):
        instance = Mock()
        instance.password_data = Mock(return_value={'PasswordData': ''})
        self.password_waiter.wait = Mock(return_value=self.encrypted)

        res = self.credentials_service.get_windows_credentials(instance, ''.join(self.pem))
        self.assertEquals(self.decrypted, self.credentials_service.decrypt_password(self.pem, self.encrypted), res.password)
        self.assertEquals('Administrator', res.user_name, InstanceCredentialsService.DEFAULT_USER_NAME)
