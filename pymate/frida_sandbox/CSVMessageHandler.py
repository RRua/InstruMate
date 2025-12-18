from pymate.frida_sandbox.CSVLogger import CSVLogger
from pymate.frida_sandbox.MessageHandler import MessageHandler
from pymate.frida_sandbox.JsonToColumnsConverter import JsonToColumnsConverter


class CSVMessageHandler(MessageHandler):
    def __init__(self, base_dir, handled_msg_type, columns_converter: JsonToColumnsConverter, quiet=False):
        self.quiet = quiet
        self.handled_msg_type = handled_msg_type
        self.csv_intercepted = CSVLogger(base_dir, "FRIDA_SANDBOX_%s.csv" % handled_msg_type, columns_converter)

    def can_handle(self, message_type):
        if message_type == self.handled_msg_type:
            return True
        return False

    def handle_message(self, message_type, message):
        if not self.csv_intercepted.is_open:
            data = self.csv_intercepted.open_log(message)
        else:
            data = self.csv_intercepted.append_log(message)

    def stop(self):
        if self.csv_intercepted.is_open:
            self.csv_intercepted.close_log()