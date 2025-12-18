import logging
from typing import Callable
import traceback
import time
from pymate.device_link.device_pool import DevicePool


class DeviceLinkCommander:
    # Class variable to keep track of the number of instances
    _id_counter = -1

    def __init__(self, device_pool: DevicePool, output_dir: str):
        DeviceLinkCommander._id_counter += 1
        self.ID = DeviceLinkCommander._id_counter
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device_pool = device_pool
        self.output_dir = output_dir
        self.default_delay_after_failure = 10
        self.default_delay_after_success = 5

    def _execute_device_link_command(self, func: Callable, logger_func: Callable, attempts=3, *args, **kwargs):
        attempt_index = 0
        success = False
        tb_exception = None
        stdout = None
        stderr = None
        while not success and attempt_index < attempts:
            start_time = time.time()
            try:
                success, stdout, stderr = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger_func(success, duration, attempt_index, stdout, stderr, tb_exception, *args, **kwargs)
                if not success:
                    attempt_index = attempt_index + 1
                    time.sleep(self.default_delay_after_failure)
            except Exception:
                tb_exception = traceback.format_exc()
                end_time = time.time()
                duration = end_time - start_time
                logger_func(success, duration, attempt_index, stdout, stderr, tb_exception, *args, **kwargs)
                attempt_index = attempt_index + 1
                time.sleep(self.default_delay_after_failure)
        if success:
            time.sleep(self.default_delay_after_success)
        return success