from contextlib import contextmanager
import sys

from botocore.exceptions import ClientError


class ClientErrorWrapper(object):

    @contextmanager
    def wrap(self):
        try:
            yield
        except ClientError as e:
            raise type(e), \
                type(e)('AWS API Error. Please consider retrying the operation. ' + e.message), \
                sys.exc_info()[2]
