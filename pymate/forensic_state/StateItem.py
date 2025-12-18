from abc import abstractmethod


class StateItem:

    @abstractmethod
    def get_time_tag(self):
        raise NotImplementedError()

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError()

    @abstractmethod
    def get_signature(self):
        raise NotImplementedError()

    @abstractmethod
    def is_different(self, other):
        raise NotImplementedError()

    @abstractmethod
    def get_differences(self, other):
        raise NotImplementedError()
