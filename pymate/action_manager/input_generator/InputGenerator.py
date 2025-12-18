from abc import abstractmethod
from pymate.action_manager.graph import UIActionUnit
import random
import string


class InputGenerator:

    @abstractmethod
    def generate(self, action_unit: UIActionUnit):
        raise NotImplementedError()


class RandomInputGenerator(InputGenerator):
    def __init__(self, min_len=4, max_len=30):
        self.min_len = min_len
        self.max_len = max_len

    def generate(self, action_unit: UIActionUnit):
        characters = string.ascii_letters + string.digits + " "
        length = random.randint(self.min_len, self.max_len)
        random_string = ''.join(random.choice(characters) for _ in range(length))
        return random_string
