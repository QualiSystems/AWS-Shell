from retrying import retry


@retry(stop_max_attempt_number=10, wait_fixed=2000)
def do_with_retry(action):
    action()
