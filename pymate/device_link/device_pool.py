import logging
import threading
import time
from collections import deque
from pymate.device_link.device_link import DeviceLink, list_adb_devices

DEFAULT_RESTORE_SNAPSHOT_TIMEOUT = 30
DEFAULT_REBOOT_TIMEOUT = 240


class DevicePool:
    def __init__(self, serial_numbers=None, emulator_restore_snapshot=None, reboot_device_on_release=True, recycle_emulator_with_kill=False,
                 restore_snapshot_timeout=DEFAULT_RESTORE_SNAPSHOT_TIMEOUT, reboot_timeout=DEFAULT_REBOOT_TIMEOUT):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.emulator_restore_snapshot = emulator_restore_snapshot
        self.reboot_device_on_release = reboot_device_on_release
        self.restore_snapshot_timeout = restore_snapshot_timeout
        self.reboot_timeout = reboot_timeout
        if serial_numbers is None:
            serial_numbers = list_adb_devices()
        self.size = len(serial_numbers)
        if self.size == 0:
            raise RuntimeError(f"No devices available...")
        self.buffer = deque(maxlen=self.size)
        self.empty = threading.Semaphore(self.size)
        self.filled = threading.Semaphore(0)
        self.buffer_lock = threading.Lock()
        self.recycle_emulator_with_kill = recycle_emulator_with_kill
        self.max_kill_retry = 3
        for item in serial_numbers:
            device_link = DeviceLink()
            device_link.configure_device(serialno=item)
            self.release(device_link, skip_recycle=True)
        self.logger.info(f"DevicePool initialized with {self.size} devices.")

    def get(self):
        item: DeviceLink = None
        self.filled.acquire()
        with self.buffer_lock:
            item = self.buffer.popleft()
            self.size = len(self.buffer)
            self.logger.debug(f"Pool provided device_link {item.serialno}")
        self.empty.release()
        return item

    def recycle(self, device_link: DeviceLink):
        if self.recycle_emulator_with_kill:
            self.logger.info(f"Killing emulator {device_link.serialno}")
            kill_attempt_count = 0
            is_killed = False
            while not is_killed and kill_attempt_count < self.max_kill_retry:
                is_killed = device_link.kill_emulator()
                kill_attempt_count = kill_attempt_count + 1
            self.logger.info(
                f"Emulator {device_link.serialno} was killed or was already dead attempts {kill_attempt_count} vs {self.max_kill_retry}."
                f" Waiting {self.reboot_timeout}s")
            time.sleep(self.reboot_timeout)
        else:
            if self.emulator_restore_snapshot is not None:
                self.logger.debug(f"Restoring snapshot for device {device_link.serialno}")
                device_link.restore_emulator_snapshot(self.emulator_restore_snapshot)
                self.logger.debug(
                    f"Restored snapshot to {self.emulator_restore_snapshot}. Waiting {self.restore_snapshot_timeout}s")
                time.sleep(self.restore_snapshot_timeout)
            if self.reboot_device_on_release:
                self.logger.debug(f"Rebooting device {device_link.serialno}")
                device_link.reboot()
                self.logger.debug(f"Sent reboot command to {device_link.serialno}. Waiting {self.reboot_timeout}s")
                time.sleep(self.reboot_timeout)
        device_link.wait_to_be_ready()
        self.logger.info(f"DeviceLink {device_link.serialno} was recycled and ready to be returned to the pool")

    def release(self, device_link: DeviceLink, skip_recycle=False):
        if not skip_recycle:
            self.recycle(device_link)
        self.empty.acquire()
        with self.buffer_lock:
            self.buffer.append(device_link)
            self.size = len(self.buffer)
        self.filled.release()

    def get_size(self):
        return self.size

    def shutdown(self):
        with self.buffer_lock:
            for item in self.buffer:
                item.close_connection()



def main():
    adb_devices = list_adb_devices()
    device_pool = DevicePool(serial_numbers=adb_devices, emulator_restore_snapshot="snap-start")
    def worker():
        while True:
            device_link = device_pool.get()
            try:
                installed_apps = device_link.get_installed_apps()
                print("----------")
                print(f"Using device {device_link.serialno} with {len(installed_apps)} installed apps")
                print("----------")
            finally:
                device_pool.release(device_link)
    worker1 = threading.Thread(target=worker)
    worker2 = threading.Thread(target=worker)
    worker1.start()
    worker2.start()
    worker1.join()
    worker2.join()

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()