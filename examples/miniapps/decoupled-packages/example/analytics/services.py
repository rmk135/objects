"""Analytics services module."""


from ..abstraction.analytics.services import AggregationServiceMeta
from ..abstraction.photo.repositories import PhotoRepositoryMeta
from ..abstraction.user.repositories import UserRepositoryMeta


class AggregationService(AggregationServiceMeta):

    def __init__(self, user_repository: UserRepositoryMeta, photo_repository: PhotoRepositoryMeta):
        self.user_repository: UserRepositoryMeta = user_repository
        self.photo_repository: PhotoRepositoryMeta = photo_repository

    def call_user_photo(self):
        user1 = self.user_repository.get(id=1)
        user1_photos = self.photo_repository.get_photos(user1.id)
        print(f"Retrieve user id={user1.id}, photos count={len(user1_photos)} from aggregation service.")
