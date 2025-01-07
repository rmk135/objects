"""Resources module."""

import abc
from typing import TypeVar, Generic, Optional


T = TypeVar("T")


class Resource(Generic[T], metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def init(self, *args, **kwargs) -> Optional[T]:
        ...

    def shutdown(self, resource: Optional[T]) -> None:
        ...


class AsyncResource(Generic[T], metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def init(self, *args, **kwargs) -> Optional[T]:
        ...

    async def shutdown(self, resource: Optional[T]) -> None:
        ...


class AsyncShutdownResource(Generic[T], metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def init(self, *args, **kwargs) -> Optional[T]:
        ...

    async def shutdown(self, resource: Optional[T]) -> None:
        ...
