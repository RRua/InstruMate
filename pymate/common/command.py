import logging
import subprocess
import threading
import base64


def decode_outputs(line):
    try:
        line_decoded = line.decode('utf-8')
    except UnicodeDecodeError:
        try:
            line_decoded = line.decode('latin-1')
        except UnicodeDecodeError:
            try:
                line_decoded = line.decode('ascii')
            except UnicodeDecodeError:
                line_decoded = "base64:"+base64.b64encode(line).decode('ascii')
    return line_decoded

class CommandOutputCapturer:
    def __init__(self):
        self._lock_stdout = threading.Lock()
        self._lock_stderr = threading.Lock()
        self.stdout_data = []
        self.stderr_data = []

    def append_stdout(self, stdout):
        with self._lock_stdout:
            self.stdout_data.append(stdout)

    def append_stderr(self, stderr):
        with self._lock_stdout:
            self.stdout_data.append(stderr)

    def collect(self):
        collected_stdout = []
        collected_stderr = []
        with self._lock_stdout:
            collected_stdout = self.stdout_data
            self.stdout_data = []
        with self._lock_stderr:
            collected_stderr = self.stderr_data
            self.stderr_data = []
        return collected_stdout, collected_stderr


class Command:
    def __init__(self, cmd=None, stdout_file=None, stderr_file=None, use_in_memory_output_capturer=False, debug = False, produces_binary_output = False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cmd = cmd
        self.process = None
        self.stdout = None
        self.stderr = None
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.killed = False
        self.debug = debug
        self.produces_binary_output = produces_binary_output
        if use_in_memory_output_capturer:
            if self.stdout_file is not None or self.stderr_file is not None:
                raise NotImplementedError("Can't save output to both memory and file at the same time")
            self.output_capturer = CommandOutputCapturer()
        else:
            self.output_capturer = None

    def collect_outputs(self):
        if self.stdout_file is None and self.stderr_file is None and self.output_capturer is None:
            return self.stdout, self.stderr
        else:
            if self.output_capturer is not None:
                return self.output_capturer.collect()
            else:
                return self.stdout_file, self.stderr_file

    def run(self, timeout=60 * 60 * 2, block=False):
        def target():
            if self.stdout_file is None and self.stderr_file is None and self.output_capturer is None:
                self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                if not self.produces_binary_output:
                    self.stdout = decode_outputs(stdout)
                    self.stderr = decode_outputs(stderr)
                else:
                    self.stdout = stdout
                    self.stderr = stderr
            else:
                if self.output_capturer is not None:
                    if self.produces_binary_output:
                        raise RuntimeError("memory capturer is not available to binary files")
                    self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    def capture_stdout(pipe, capturer: CommandOutputCapturer):
                        for line in iter(pipe.readline, ''):
                            line_decoded = decode_outputs(line)
                            if self.debug:
                                self.logger.debug(f"STDOUT: {line_decoded}")
                            capturer.append_stdout(line_decoded)
                            if self.killed:
                                break

                    def capture_stderr(pipe, capturer: CommandOutputCapturer):
                        for line in iter(pipe.readline, ''):
                            line_decoded = decode_outputs(line)
                            if self.debug:
                                self.logger.debug(f"STDERR: {line_decoded}")
                            capturer.append_stderr(line_decoded)
                            if self.killed:
                                break

                    stdout_thread = threading.Thread(target=capture_stdout, args=(self.process.stdout, self.output_capturer))
                    stderr_thread = threading.Thread(target=capture_stderr, args=(self.process.stderr, self.output_capturer))
                    stdout_thread.start()
                    stderr_thread.start()
                    self.process.wait()
                    stdout_thread.join()
                    stderr_thread.join()
                else:
                    with open(self.stdout_file, 'w') as stdout_file:
                        with open(self.stderr_file, 'w') as stderr_file:
                            self.process = subprocess.Popen(self.cmd, stdout=stdout_file, stderr=stderr_file)
                            _, _ = self.process.communicate()
                            self.stdout = f"file: {self.stdout_file}"
                            self.stderr = f"file: {self.stderr_file}"
            pid = self.process.pid if self.process is not None else None
            self.logger.debug(f"Subprocess created. PID: {pid}, timeout: ({timeout}s), CMD: {str(self.cmd)}.")

        thread = threading.Thread(target=target)
        thread.start()
        if timeout > 0:
            thread.join(timeout)
            if thread.is_alive():
                self.logger.warning(f"Timeout reached ({timeout}s). Forcing process {str(self.cmd)} to terminate")
                self.process.kill()
                thread.join()
                self.logger.debug(f"Process {str(self.cmd)} finished after kill")
            else:
                returncode = self.process.returncode if self.process is not None else None
                self.logger.debug(f"Process {str(self.cmd)} finished with return code {returncode}")
        else:
            if block:
                thread.join()
                returncode = self.process.returncode if self.process is not None else None
                self.logger.debug(f"Process {str(self.cmd)} finished with return code {returncode}")
            else:
                self.logger.debug(f"Background Process started. CMD: {str(self.cmd)}")

    def kill(self):
        self.killed = True
        if self.process is not None:
            try:
                self.logger.debug(f"Killing process. CMD: {str(self.cmd)}.")
                self.process.kill()
            except Exception as e:
                self.logger.warning(f"Error killing process {e}")