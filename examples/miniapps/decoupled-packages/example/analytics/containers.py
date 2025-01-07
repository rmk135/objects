"""Analytics containers module."""

from dependency_injector import containers, providers

from . import services

from ..abstraction.photo.repositories import PhotoRepositoryMeta
from ..abstraction.user.repositories import UserRepositoryMeta


class AnalyticsContainer(containers.DeclarativeContainer):

    user_repository: UserRepositoryMeta = providers.Dependency()
    photo_repository: PhotoRepositoryMeta = providers.Dependency()

    aggregation_service = providers.Singleton(
        services.AggregationService,
        user_repository=user_repository,
        photo_repository=photo_repository,
    )
