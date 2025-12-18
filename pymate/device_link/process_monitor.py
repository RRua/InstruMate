import threading
import logging
import time
import subprocess


class ProcessMonitor:
    
    def __init__(self, device_link=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device_link = device_link
        self.pid2user = {}
        self.pid2ppid = {}
        self.pid2name = {}
        self.get_process_mapping()

    def get_process_mapping(self):
        if self.device_link is not None:
            ps_cmd = ["adb", "-s", self.device_link.androidSerial, "shell", "ps"]
        else:
            raise RuntimeError("Device link must be not none")

        try:
            ps_out = subprocess.check_output(ps_cmd)
            if not isinstance(ps_out, str):
                ps_out = ps_out.decode()
        except subprocess.CalledProcessError:
            self.logger.warning("Process monitor has errors")

        # parse ps_out to update self.pid2uid mapping and self.pid2name mapping
        ps_out_lines = ps_out.splitlines()
        ps_out_head = ps_out_lines[0].split()
        if ps_out_head[0] != "USER" or ps_out_head[1] != "PID" \
                or ps_out_head[2] != "PPID" or ps_out_head[-1] != "NAME":
            self.device.logger.warning("ps command output format error: %s" % ps_out_head)

        for ps_out_line in ps_out_lines[1:]:
            segs = ps_out_line.split()
            if len(segs) < 4:
                continue
            user = segs[0]
            pid = segs[1]
            ppid = segs[2]
            name = segs[-1]
            self.pid2name[pid] = name
            self.pid2ppid[pid] = ppid
            self.pid2user[pid] = user
        time.sleep(1)

    def get_ppids_by_pid(self, pid):
        ppids = []
        while pid in self.pid2ppid:
            ppids.append(pid)
            pid = self.pid2ppid[pid]
        ppids.reverse()
        return ppids

    def get_names_by_pid(self, pid):
        ppids = self.get_ppids_by_pid(pid)
        names = []
        for ppid in ppids:
            names.append(self.pid2name[ppid])
        return names

    def is_frida_running(self):
        for key in self.pid2name:
            value = self.pid2name[key]
            if "frida" in value.lower():
                return True
        return False
