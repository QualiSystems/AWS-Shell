from botocore.exceptions import ClientError
from retrying import retry


@retry(stop_max_attempt_number=10, wait_fixed=2000)
def do_with_retry(action):
    action()


def retry_if_client_error(exception):
    """Return True if we should retry (in this case when it's an IOError), False otherwise"""
    return isinstance(exception, ClientError)
