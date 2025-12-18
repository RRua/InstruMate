import os
from pymate.frida_sandbox.MessageHandler import MessageHandler

LOG_DEBUG = "DEBUG"
LOG_INFO = "INFO"
MAP_LEVEL_INT = {
    "DEBUG": 0,
    "INFO": 1
}


class LoggingMessageHandler(MessageHandler):
    def __init__(self, base_dir, print_level="INFO", file_level="DEBUG"):
        self.base_dir = base_dir
        self.print_level = print_level
        self.print_level_int = MAP_LEVEL_INT[print_level]
        self.file_level = file_level
        self.file_level_int = MAP_LEVEL_INT[file_level]
        self.handled_msg_type = 'INTERNAL_LOGGING'
        self.file_path = os.path.join(base_dir, "FRIDA_SANDBOX_%s.log" % self.handled_msg_type)
        self.log_file = open(self.file_path, 'w', encoding='utf-8')

    def can_handle(self, message_type):
        if message_type == self.handled_msg_type:
            return True
        return False

    def handle_message(self, message_type, message):
        level = message["level"]
        message = message["message"]
        level_int = MAP_LEVEL_INT[level]
        if level_int >= self.print_level_int:
            print(f"{level}: {message}")
        if level_int >= self.file_level_int:
            self.log_file.write(f"{level}: {message}\n")

    def stop(self):
        self.log_file.close()

