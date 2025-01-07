"""Analytics services module."""

import abc


from ..photo.repositories import PhotoRepositoryMeta
from ..user.repositories import UserRepositoryMeta


class AggregationServiceMeta(metaclass=abc.ABCMeta):

    def __init__(self, user_repository: UserRepositoryMeta, photo_repository: PhotoRepositoryMeta):
        self.user_repository: UserRepositoryMeta = user_repository
        self.photo_repository: PhotoRepositoryMeta = photo_repository

    @abc.abstractmethod
    def call_user_photo(self):
        """Must be implemented in order to instantiate."""
        pass
