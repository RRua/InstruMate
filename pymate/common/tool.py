import logging
import traceback
from datetime import datetime
from abc import abstractmethod
from pymate.common.command import Command


class BaseTool:

    def __init__(self, name: str, description: str = None, cmd: Command = None, options: dict = None):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cmd = cmd
        self.options = options if options is not None else {}

    def before_exec(self):
        pass

    def after_exec(self):
        pass

    def exec_script(self) -> (str, str):
        return None,None

    def exec_cmd(self):
        if self.cmd is not None:
            self.cmd.run()
            self.logger.debug(f"Command run(): {self.cmd.cmd}")
        else:
            self.logger.debug("Command is empty")

    def execute(self):
        start_time = datetime.now()
        tb_exception = None
        success = False
        script_stdout = None
        script_stderr = None
        try:
            self.before_exec()
            script_stdout, script_stderr = self.exec_script()
            if self.cmd is not None and self.cmd.cmd is not None:
                parameters = " ".join(self.cmd.cmd)
            else:
                parameters = ""
            self.logger.debug(f"CMD {self.name} initiated at {start_time}. Parameters: {parameters}")
            self.exec_cmd()
            self.logger.debug(f"CMD {self.name} finished at {datetime.now()}")
            self.after_exec()
            success = True
        except Exception:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            if self.cmd is not None:
                if self.cmd.cmd is not None:
                    self.logger.debug("CMD_______")
                    self.logger.debug(" ".join(self.cmd.cmd))
                self.logger.debug("STDOUT_______")
                self.logger.debug(self.cmd.stdout)
                self.logger.debug("STDERR_______")
                self.logger.debug(self.cmd.stderr)
            self.logger.debug("SCRIPT-STDOUT------")
            self.logger.debug(script_stdout)
            self.logger.debug("SCRIPT-STDERR------")
            self.logger.debug(script_stderr)
        end_time = datetime.now()
        total_secs = (end_time - start_time).total_seconds()
        cmd_stdout = self.cmd.stdout if self.cmd is not None else None
        cmd_stderr = self.cmd.stderr if self.cmd is not None else None
        return {
            "name": self.name,
            "description": self.description,
            "success": success,
            "cmd_stdout": cmd_stdout,
            "cmd_stderr": cmd_stderr,
            "script_stdout": script_stdout,
            "script_stderr": script_stderr,
            "traceback_exception": tb_exception,
            "total_secs": total_secs,
            "options": self.options
        }
