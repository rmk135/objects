"""Photo repositories Meta module."""

import abc


class PhotoRepositoryMeta(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_photos(self, user_id):
        """Must be implemented in order to instantiate."""
        pass
