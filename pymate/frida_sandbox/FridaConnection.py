import frida
from pymate.frida_sandbox.CSVMessageHandler import CSVMessageHandler
from pymate.frida_sandbox.MessageHandler import MessageHandler
from pymate.frida_sandbox.JsonToColumnsConverter import JMethodConverter, ModuleConverter
from pymate.frida_sandbox.LoggingMessageHandler import LoggingMessageHandler
from pymate.frida_sandbox.SensitiveApisCollector import SensitiveApisCollector
from pymate.frida_sandbox.LoadedModulesCollector import LoadedModulesCollector
from pymate.frida_sandbox.DetailedSandboxCollector import DetailedSandboxCollector
from pymate.frida_sandbox.SandboxStateCollector import SandboxStateCollector
from pymate.frida_sandbox.ControlledEnumerationHandler import ControlledEnumerationHandler
from pymate.utils.utils import is_dictionary


class FridaConnection:
    def __init__(self, app_package, compiled_script):
        self.app_package = app_package
        self.compiled_script = compiled_script
        self.message_handlers = []
        self.script_obj = None
        self.qtd_messages_rcv = 0
        self.is_started = False

    def add_message_handler(self, message_handler: MessageHandler):
        self.message_handlers.append(message_handler)

    def get_message_handler(self, cls):
        for handler in self.message_handlers:
            if isinstance(handler, cls):
                return handler
        return None

    def start(self):
        if not self.is_started:
            device = frida.get_usb_device()
            pid = device.spawn(self.app_package)
            session = device.attach(pid)
            self.script_obj = session.create_script(self.compiled_script)
            self.script_obj.on('message', self.on_message)
            self.script_obj.load()
            device.resume(pid)
            self.is_started = True

    def get_is_started(self):
        return self.is_started

    def stop(self):
        if self.is_started:
            for handler in self.message_handlers:
                handler.stop()
            self.script_obj.unload()

    def on_message(self, message, data):
        if is_dictionary(message):
            if 'payload' in message:
                payload = message["payload"]
                messageType = payload["messageType"]
                message = payload["message"]
                for handler in self.message_handlers:
                    if handler.can_handle(messageType):
                        handler.handle_message(messageType, message)
                self.qtd_messages_rcv = self.qtd_messages_rcv + 1
        else:
            print("Message is not dict: " + str(message))

    @staticmethod
    def create_frida_connection(base_dir, app_package, compiled_script):
        frida_connection = FridaConnection(app_package, compiled_script)
        java_method_msg_handler = CSVMessageHandler(base_dir=base_dir, handled_msg_type="JAVA_METHOD_INTERCEPTED",
                                                    columns_converter=JMethodConverter())
        logging_msg_handler = LoggingMessageHandler(base_dir=base_dir)
        sensitive_apis_collector = SensitiveApisCollector()
        loaded_modules_collector = LoadedModulesCollector()
        detailed_apis_collector = DetailedSandboxCollector(handled_msg_type="JAVA_METHOD_INTERCEPTED",
                                                           columns_converter=JMethodConverter())
        sandbox_state_collector = SandboxStateCollector()
        controlled_enumeration = ControlledEnumerationHandler(base_dir=base_dir,
                                                              sandbox_state_collector=sandbox_state_collector)

        frida_connection.add_message_handler(java_method_msg_handler)
        frida_connection.add_message_handler(controlled_enumeration)
        frida_connection.add_message_handler(logging_msg_handler)
        frida_connection.add_message_handler(sensitive_apis_collector)
        frida_connection.add_message_handler(loaded_modules_collector)
        frida_connection.add_message_handler(detailed_apis_collector)
        frida_connection.add_message_handler(sandbox_state_collector)
        return frida_connection


def main():
    temp = open("./tmp/output.js", 'r', encoding='utf8', newline='\n')
    temp.seek(0)
    compiled_script = temp.read()
    frida_connection = FridaConnection(app_package="com.whatsapp", compiled_script=compiled_script)
    java_method_msg_handler = CSVMessageHandler(base_dir="./tmp", handled_msg_type="JAVA_METHOD_INTERCEPTED",
                                                columns_converter=JMethodConverter())
    module_msg_handler = CSVMessageHandler(base_dir="./tmp", handled_msg_type="MODULE_ENUMERATION",
                                           columns_converter=ModuleConverter())
    logging_msg_handler = LoggingMessageHandler(base_dir="./tmp")
    sensitive_apis_collector = SensitiveApisCollector()
    loaded_modules_collector = LoadedModulesCollector()
    detailed_apis_collector = DetailedSandboxCollector(handled_msg_type="JAVA_METHOD_INTERCEPTED",
                                                       columns_converter=JMethodConverter())
    sandbox_state_collector = SandboxStateCollector()

    frida_connection.add_message_handler(java_method_msg_handler)
    frida_connection.add_message_handler(module_msg_handler)
    frida_connection.add_message_handler(logging_msg_handler)
    frida_connection.add_message_handler(sensitive_apis_collector)
    frida_connection.add_message_handler(loaded_modules_collector)
    frida_connection.add_message_handler(detailed_apis_collector)
    frida_connection.add_message_handler(sandbox_state_collector)
    frida_connection.start()
    while True:
        print("QTD msgs rcv %d " % frida_connection.qtd_messages_rcv)
        answer = input("Enter 'y' to quit, or any other key to continue: ")
        if answer.lower() == "y":
            break
        collected = sandbox_state_collector.collect()
        for item in collected:
            print(f"{item}: {collected[item]}")
    frida_connection.stop()
    print("Loop ended!")


if __name__ == "__main__":
    main()
