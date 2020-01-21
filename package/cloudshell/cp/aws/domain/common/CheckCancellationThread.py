import threading
import time


class CheckCancellationThread(threading.Thread):
    def __init__(self, cancellation_context, cancellation_service):
        super(CheckCancellationThread, self).__init__()
        self._stop = threading.Event()
        self.cancellation_context = cancellation_context
        self.cancellation_service = cancellation_service

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def run(self):
        while True:
            if self.stopped():
                return
            time.sleep(1)
            cancelled = self.cancellation_service.check_if_cancelled(self.cancellation_context)
            if cancelled:
                raise Exception('User cancelled traffic mirroring')

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()