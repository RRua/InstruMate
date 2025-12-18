from pymate.frida_sandbox.MessageHandler import MessageHandler
from pymate.frida_sandbox.JsonToColumnsConverter import JsonToColumnsConverter
import threading


class DetailedSandboxCollector(MessageHandler):
    def __init__(self, handled_msg_type, columns_converter: JsonToColumnsConverter):
        self.handled_msg_type = handled_msg_type
        self.columns_converter = columns_converter
        self.lock = threading.Lock()
        self.collection = []

    def can_handle(self, message_type):
        if message_type == self.handled_msg_type:
            return True
        return False

    def handle_message(self, message_type, message):
        with self.lock:
            if len(self.collection) == 0:
                header = self.columns_converter.get_header()
                self.collection.append(header)
            values = self.columns_converter.get_values(message)
            self.collection.append(values)

    def stop(self):
        pass

    def collect(self):
        new_list = None
        with self.lock:
            new_list = list(self.collection)
            self.collection.clear()
        return new_list
