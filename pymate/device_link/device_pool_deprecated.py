import logging
import threading
import time
import traceback
from pymate.common.command import Command
from pymate.device_link.device_link import DeviceLink









class DevicePool_deprecated:
    def __init__(self, emulator_restore_snapshot = None, reboot_device_on_release = False, thread_safe=True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pool = []
        self.emulator_restore_snapshot = emulator_restore_snapshot
        self.reboot_device_on_release = reboot_device_on_release
        self.thread_safe = thread_safe
        self.restore_snapshot_restore = 5*60
        self.reboot_timeout_wait = 5*60
        self.removed_devices = []
        self.retry_connect_max_attempts = 3
        self.retry_connect_delay = 30
        if self.thread_safe:
            self.lock = threading.Lock()

    def add_all_connected_devices(self):
        try:
            if self.thread_safe:
                self.lock.acquire()
            adb_devices = self._list_adb_devices()
            for device_serial in adb_devices:
                device_link = DeviceLink()
                device_link.configure_device(serialno=device_serial)
                self.pool.append(device_link)
                self.logger.info(f"Device {device_serial} added to the pool")
        finally:
            if self.thread_safe:
                self.lock.release()

    def get(self):
        try:
            if self.thread_safe:
                self.lock.acquire()
            if self.pool and len(self.pool) > 0:
                device_link = self.pool.pop(0)
                self.removed_devices.append(device_link.serialno)
                return device_link
            else:
                if len(self.removed_devices) > 0:
                    while True:
                        connected_devices = self._list_adb_devices()
                        for connected_device in connected_devices:
                            if connected_device in self.removed_devices:
                                device_link = DeviceLink()
                                device_link.configure_device(serialno=connected_device)
                                self.pool.append(device_link)
                                self.removed_devices.remove(connected_device)
                        if self.pool and len(self.pool) > 0:
                            device_link = self.pool.pop(0)
                            self.removed_devices.append(device_link.serialno)
                            return device_link
                        else:
                            self.logger.debug(f"Still without devices to return...")
                            time.sleep(self.retry_connect_delay)
                else:
                    raise Exception("No available resources")
        finally:
            if self.thread_safe:
                self.lock.release()

    def _list_adb_devices(self):
        result = []
        cmd_list = ["adb", "devices"]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        lines = stdout.splitlines()
        if len(lines) == 0:
            raise RuntimeError(f"Error collecting list of devices: {stdout} - {stderr}")
        if lines[0] != 'List of devices attached':
            raise RuntimeError(f"Did adb return the list of connected devices? {stdout} - {stderr}")
        for line in lines:
            if 'device' in line and line != 'List of devices attached':
                device_serial = line.split()[0]
                result.append(device_serial)
        self.logger.debug(f"Adb devices available {str(result)}")
        return result

    def _clear_device_link(self, device_link):
        try:
            if self.emulator_restore_snapshot is not None:
                self.logger.info(f"Restoring snapshot for device {device_link.serialno}")
                device_link.restore_emulator_snapshot(self.emulator_restore_snapshot)
                self.logger.debug(f"Restored snapshot to {self.emulator_restore_snapshot}. Waiting {self.restore_snapshot_restore}s")
                time.sleep(self.restore_snapshot_restore)
            if self.reboot_device_on_release:
                self.logger.info(f"Rebooting device {device_link.serialno}")
                device_link.reboot()
                self.logger.debug(f"Sent reboot command to {device_link.serialno}. Waiting {self.reboot_timeout_wait}s")
                time.sleep(self.reboot_timeout_wait)
            retry_num = 0
            device_on = False
            while retry_num < self.retry_connect_max_attempts and not device_on:
                adb_devices = self._list_adb_devices()
                if device_link.serialno in adb_devices:
                    self.logger.debug(f"Device {device_link.serialno} can be reconnected")
                    device_on = True
                else:
                    self.logger.debug(f"Waiting for device {device_link.serialno}")
                    time.sleep((retry_num+1)*self.retry_connect_delay)
                retry_num = retry_num + 1
            if device_on:
                installed_apps = device_link.get_installed_apps()
                self.logger.debug(f"Device-link cleaned {device_link.serialno}. Installed apps {len(installed_apps)}")
                return True
            else:
                return False
        except:
            self.logger.warning(f"Device-link failed to be cleaned {device_link.serialno}.")
            tb_exception = traceback.format_exc()
            self.logger.warning(tb_exception)
            return False

    def release(self, device_link: DeviceLink):
        def clear_device_before_reuse():
            if self._clear_device_link(device_link):
                try:
                    if self.thread_safe:
                        self.lock.acquire()
                    self.pool.append(device_link)
                finally:
                    if self.thread_safe:
                        self.lock.release()
        thread = threading.Thread(target=clear_device_before_reuse)
        thread.start()

    def size(self):
        try:
            if self.thread_safe:
                self.lock.acquire()
            return len(self.pool)
        finally:
            if self.thread_safe:
                self.lock.release()

    def shutdown(self):
        try:
            if self.thread_safe:
                self.lock.acquire()
            self.pool.clear()
        finally:
            if self.thread_safe:
                self.lock.release()



def main():
    device_pool = DevicePool(emulator_restore_snapshot='snap-start', reboot_device_on_release=True, thread_safe=True)
    device_pool.add_all_connected_devices()
    while True:
        print(f"Getting device link: ")
        device_link = device_pool.get()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    main()