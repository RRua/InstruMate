from abc import abstractmethod


class StateObserver:

    @abstractmethod
    def observe(self):
        raise NotImplementedError()

    @abstractmethod
    def has_changed(self):
        raise NotImplementedError()

    @abstractmethod
    def get_state(self):
        raise NotImplementedError()

    @abstractmethod
    def get_last_state(self):
        raise NotImplementedError()

    @abstractmethod
    def save_2_folder(self, folder):
        raise NotImplementedError()
