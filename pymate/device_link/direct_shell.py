import socket
import errno
import logging
import time
from datetime import datetime
from pymate.device_link import DeviceLink

BUFFER_SIZE = 4096
TIMEOUT = 1
MAX_READ_ERRORS = 10
PROGRAM_FINISH_MARKER = 'fm-program-end-end-program-fm'


class DirectShell:
    def __init__(self, device_link: DeviceLink, ip_addr=None, port=8880, use_device_ip_addr=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ip_addr = ip_addr
        self.port = port
        self.socket = None
        self.buffered_reader = None
        self.use_device_ip_addr = use_device_ip_addr
        self.device_link = device_link
        if not use_device_ip_addr or ip_addr is None:
            device_link.adb_forward_tcp_port(port,port)
            self.ip_addr = "127.0.0.1"

    def check_connection(self):
        result = self.send_command("whoami")
        if len(result) == 1:
            me_str = result[0]
            if me_str != 'root':
                raise RuntimeError("Direct shell must be called by root")
            else:
                self.logger.info("Connected")
        else:
            raise RuntimeError("Direct shell not connected")

    def send_command(self, command):
        final_command = "%s; echo \"%s\";\n" % (command, PROGRAM_FINISH_MARKER)
        self.socket.sendall(final_command.encode('utf-8'))
        buffer = []
        read_err_count = 0
        while True:
            try:
                part = self.socket.recv(BUFFER_SIZE)
            except socket.timeout:
                part = None
                read_err_count = read_err_count + 1
            except socket.error as e:
                if e.errno == errno.EWOULDBLOCK:
                    part = None
                    read_err_count = read_err_count + 1
                else:
                    import traceback
                    traceback.print_exc()
                    raise RuntimeError("Direct Shell socket error")
            if not part:
                if read_err_count > MAX_READ_ERRORS:
                    raise RuntimeError("Truncated response from direct shell")
            else:
                part_as_str = part.decode('utf-8')
                buffer.append(part_as_str)
                if PROGRAM_FINISH_MARKER in part_as_str:
                    break
        data = ''.join(buffer)
        res_lines = data.splitlines()
        sub_array1 = res_lines[:-1]
        sub_array2 = res_lines[-1:]
        if len(sub_array2) == 1 and sub_array2[0] == PROGRAM_FINISH_MARKER:
            return sub_array1
        else:
            raise RuntimeError("Truncated response from direct shell")

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.ip_addr, self.port))
        self.socket.setblocking(True)
        self.socket.settimeout(TIMEOUT)
        self.check_connection()

    def list_modifications(self, base_dir, target=None):
        if target is not None:
            final_path = "%s/%s" % (base_dir, target)
        else:
            final_path = base_dir
        command = f"find {final_path} -type f -exec stat -c%Y:%n {{}} \\;"
        file_list_str = self.send_command(command)
        result = []
        for file_str in file_list_str:
            splited = file_str.split(':')
            dt_part = int(splited[0])
            file_part = splited[1]
            formatted_time = datetime.utcfromtimestamp(dt_part).strftime('%Y-%m-%d %H:%M:%S UTC')
            result.append({
                "timestamp": dt_part,
                "timestamp_fmt": formatted_time,
                "file": file_part
            })
        return result

    def create_tar(self, dest, file_list):
        final_str = ''
        for item in file_list:
            item_str = f"'{item}' "
            final_str += item_str
        command = f"tar -cvf {dest} {final_str}"
        command_result = self.send_command(command)
        return command_result


def main():
    direct_shell = DirectShell("10.1.1.108")
    direct_shell.connect()
    direct_shell.check_connection()
    start_time = time.perf_counter()
    file_list = direct_shell.list_modifications("/data/data", "com.whatsapp")
    tar_items = []
    for file in file_list:
        print(file)
        tar_items.append(file["file"])
    # direct_shell.send_command("ls -lhatr")
    end_time = time.perf_counter()
    duration = end_time - start_time
    print(f"The function took {duration} seconds to complete.")
    direct_shell.create_tar("/data/local/tmp/temp.tar", tar_items)


if __name__ == "__main__":
    main()
