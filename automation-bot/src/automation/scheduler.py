thonimport threading
import time
from typing import Callable

from .utils.logger import get_logger

class Scheduler:
    """
    A simple fixed-interval scheduler that repeatedly runs a task until interrupted.
    """

    def __init__(
        self,
        interval_seconds: int,
        task: Callable[[], None],
        logger=None,
    ):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")

        self.interval_seconds = interval_seconds
        self.task = task
        self.logger = logger or get_logger()
        self._stop_event = threading.Event()

    def _run_loop(self):
        self.logger.info("Scheduler loop started with %s second interval", self.interval_seconds)
        try:
            while not self._stop_event.is_set():
                start = time.time()
                try:
                    self.task()
                except Exception as exc:  # noqa: BLE001
                    self.logger.exception("Error while running scheduled task: %s", exc)

                elapsed = time.time() - start
                remaining = self.interval_seconds - elapsed
                if remaining > 0:
                    self.logger.debug("Sleeping for %.2f seconds until next run", remaining)
                    self._stop_event.wait(timeout=remaining)
        finally:
            self.logger.info("Scheduler loop stopped")

    def start(self, in_background: bool = False):
        """
        Start the scheduler. If in_background is True, it returns immediately and
        runs in a daemon thread. Otherwise, it blocks until stopped or interrupted.
        """
        if in_background:
            thread = threading.Thread(target=self._run_loop, daemon=True)
            thread.start()
            return thread
        else:
            self._run_loop()

    def stop(self):
        self._stop_event.set()