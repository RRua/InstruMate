import logging
from pymate.action_manager.input_generator.InputGenerator import RandomInputGenerator


class InputManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InputManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = logging.getLogger(self.__class__.__name__)
            self.initialized = True
            self.default_input_generator = RandomInputGenerator()

    def get_default_input_generator(self):
        return self.default_input_generator
