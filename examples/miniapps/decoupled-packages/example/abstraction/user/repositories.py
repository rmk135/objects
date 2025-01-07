"""User repositories meta module."""


import abc


class UserRepositoryMeta(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, id):
        """Must be implemented in order to instantiate."""
        pass
