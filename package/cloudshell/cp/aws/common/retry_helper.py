from retrying import retry


@retry(stop_max_attempt_number=3, wait_fixed=1000)
def do_with_retry(action):
    action()
