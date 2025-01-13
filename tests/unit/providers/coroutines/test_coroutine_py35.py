"""Coroutine provider tests."""
import sys

from dependency_injector import providers, errors
from pytest import mark, raises

from .common import example


def test_init_with_coroutine():
    assert isinstance(providers.Coroutine(example), providers.Coroutine)


def test_init_with_not_coroutine():
    with raises(errors.Error):
        providers.Coroutine(lambda: None)


@mark.asyncio
async def test_init_optional_provides():
    provider = providers.Coroutine()
    provider.set_provides(example)

    result = await provider(1, 2, 3, 4)

    assert result == (1, 2, 3, 4)
    assert provider.provides is example


def test_set_provides_returns_self():
    provider = providers.Coroutine()
    assert provider.set_provides(example) is provider


@mark.parametrize(
    "str_name,cls",
    [
        (".common.example", example),
        ("example", example),
    ],
)
def test_set_provides_string_imports(str_name, cls):
    assert providers.Coroutine(str_name).provides is cls


@mark.asyncio
async def test_call_with_positional_args():
    provider = providers.Coroutine(example, 1, 2, 3, 4)
    result = await provider()
    assert result == (1, 2, 3, 4)


@mark.asyncio
async def test_call_with_keyword_args():
    provider = providers.Coroutine(example, arg1=1, arg2=2, arg3=3, arg4=4)
    result = await provider()
    assert result == (1, 2, 3, 4)


@mark.asyncio
async def test_call_with_positional_and_keyword_args():
    provider = providers.Coroutine(example, 1, 2, arg3=3, arg4=4)
    result = await provider()
    assert result == (1, 2, 3, 4)


@mark.asyncio
async def test_call_with_context_args():
    provider = providers.Coroutine(example, 1, 2)
    result = await provider(3, 4)
    assert result == (1, 2, 3, 4)


@mark.asyncio
async def test_call_with_context_kwargs():
    provider = providers.Coroutine(example, arg1=1)
    result = await provider(arg2=2, arg3=3, arg4=4)
    assert result == (1, 2, 3, 4)


@mark.asyncio
async def test_call_with_context_args_and_kwargs():
    provider = providers.Coroutine(example, 1)
    result = await provider(2, arg3=3, arg4=4)
    assert result == (1, 2, 3, 4)


@mark.asyncio
async def test_fluent_interface():
    provider = providers.Coroutine(example) \
        .add_args(1, 2) \
        .add_kwargs(arg3=3, arg4=4)
    result = await provider()
    assert result == (1, 2, 3, 4)


def test_set_args():
    provider = providers.Coroutine(example) \
        .add_args(1, 2) \
        .set_args(3, 4)
    assert provider.args == (3, 4)


def test_set_kwargs():
    provider = providers.Coroutine(example) \
        .add_kwargs(init_arg3=3, init_arg4=4) \
        .set_kwargs(init_arg3=4, init_arg4=5)
    assert provider.kwargs == dict(init_arg3=4, init_arg4=5)


def test_clear_args():
    provider = providers.Coroutine(example) \
        .add_args(1, 2) \
        .clear_args()
    assert provider.args == tuple()


def test_clear_kwargs():
    provider = providers.Coroutine(example) \
        .add_kwargs(init_arg3=3, init_arg4=4) \
        .clear_kwargs()
    assert provider.kwargs == dict()


def test_call_overridden():
    provider = providers.Coroutine(example)

    provider.override(providers.Object((4, 3, 2, 1)))
    provider.override(providers.Object((1, 2, 3, 4)))

    assert provider() == (1, 2, 3, 4)


def test_deepcopy():
    provider = providers.Coroutine(example)

    provider_copy = providers.deepcopy(provider)

    assert provider is not provider_copy
    assert provider.provides is provider_copy.provides
    assert isinstance(provider, providers.Coroutine)


def test_deepcopy_from_memo():
    provider = providers.Coroutine(example)
    provider_copy_memo = providers.Coroutine(example)

    provider_copy = providers.deepcopy(provider, memo={id(provider): provider_copy_memo})

    assert provider_copy is provider_copy_memo


def test_deepcopy_args():
    provider = providers.Coroutine(example)
    dependent_provider1 = providers.Callable(list)
    dependent_provider2 = providers.Callable(dict)

    provider.add_args(dependent_provider1, dependent_provider2)

    provider_copy = providers.deepcopy(provider)
    dependent_provider_copy1 = provider_copy.args[0]
    dependent_provider_copy2 = provider_copy.args[1]

    assert dependent_provider1.provides is dependent_provider_copy1.provides
    assert dependent_provider1 is not dependent_provider_copy1

    assert dependent_provider2.provides is dependent_provider_copy2.provides
    assert dependent_provider2 is not dependent_provider_copy2


def test_deepcopy_kwargs():
    provider = providers.Coroutine(example)
    dependent_provider1 = providers.Callable(list)
    dependent_provider2 = providers.Callable(dict)

    provider.add_kwargs(a1=dependent_provider1, a2=dependent_provider2)

    provider_copy = providers.deepcopy(provider)
    dependent_provider_copy1 = provider_copy.kwargs["a1"]
    dependent_provider_copy2 = provider_copy.kwargs["a2"]

    assert dependent_provider1.provides is dependent_provider_copy1.provides
    assert dependent_provider1 is not dependent_provider_copy1

    assert dependent_provider2.provides is dependent_provider_copy2.provides
    assert dependent_provider2 is not dependent_provider_copy2


def test_deepcopy_overridden():
    provider = providers.Coroutine(example)
    object_provider = providers.Object(object())

    provider.override(object_provider)

    provider_copy = providers.deepcopy(provider)
    object_provider_copy = provider_copy.overridden[0]

    assert provider is not provider_copy
    assert provider.provides is provider_copy.provides
    assert isinstance(provider, providers.Callable)

    assert object_provider is not object_provider_copy
    assert isinstance(object_provider_copy, providers.Object)


def test_repr():
    provider = providers.Coroutine(example)
    assert repr(provider) == (
        "<dependency_injector.providers."
        "Coroutine({0}) at {1}>".format(repr(example), hex(id(provider)))
    )


@mark.skipif(sys.version_info > (3, 15), reason="requires Python<3.16")
def test_asyncio_iscoroutinefunction() -> None:
    from asyncio.coroutines import iscoroutinefunction

    assert iscoroutinefunction(providers.Coroutine(example))


@mark.skipif(sys.version_info < (3, 12), reason="requires Python>=3.12")
def test_inspect_iscoroutinefunction() -> None:
    from inspect import iscoroutinefunction

    assert iscoroutinefunction(providers.Coroutine(example))
