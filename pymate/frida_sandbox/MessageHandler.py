from abc import abstractmethod


class MessageHandler:

    @abstractmethod
    def can_handle(self, message_type):
        raise NotImplementedError()

    @abstractmethod
    def handle_message(self, message_type, message):
        raise NotImplementedError()

    @abstractmethod
    def stop(self):
        raise NotImplementedError()
