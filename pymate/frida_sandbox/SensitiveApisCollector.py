from pymate.frida_sandbox.MessageHandler import MessageHandler
import threading


class SensitiveApisCollector(MessageHandler):
    def __init__(self, clear_on_collect=False):
        self.apis = set()
        self.lock = threading.Lock()
        self.clear_on_collect = clear_on_collect
        self.clear_on_next_collection = False

    def set_clear_on_next_collection(self):
        self.clear_on_next_collection = True

    def can_handle(self, message_type):
        if message_type == "JAVA_METHOD_INTERCEPTED":
            return True
        return False

    def handle_message(self, message_type, message):
        java_signature = message["java_signature"]
        with self.lock:
            self.apis.add(java_signature)

    def stop(self):
        pass

    def collect(self, clear=False):
        new_set = None
        with self.lock:
            new_set = set(self.apis)
            if self.clear_on_collect or clear or self.clear_on_next_collection:
                self.apis.clear()
                if self.clear_on_next_collection:
                    self.clear_on_next_collection = False
        return new_set
