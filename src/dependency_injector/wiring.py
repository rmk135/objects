"""Wiring module."""

import functools
import inspect
import importlib
import importlib.machinery
import pkgutil
import warnings
import sys
from types import ModuleType
from typing import (
    Optional,
    Iterable,
    Iterator,
    Callable,
    Any,
    Tuple,
    Dict,
    Generic,
    TypeVar,
    Type,
    Union,
    Set,
    cast,
)

if sys.version_info < (3, 7):
    from typing import GenericMeta
else:
    class GenericMeta(type):
        ...

# Hotfix, see: https://github.com/ets-labs/python-dependency-injector/issues/362
if sys.version_info >= (3, 9):
    from types import GenericAlias
else:
    GenericAlias = None


try:
    import fastapi.params
except ImportError:
    fastapi = None


try:
    import starlette.requests
except ImportError:
    starlette = None


try:
    import werkzeug.local
except ImportError:
    werkzeug = None


from . import providers

if sys.version_info[:2] == (3, 5):
    warnings.warn(
        "Dependency Injector will drop support of Python 3.5 after Jan 1st of 2022. "
        "This does not mean that there will be any immediate breaking changes, "
        "but tests will no longer be executed on Python 3.5, and bugs will not be addressed.",
        category=DeprecationWarning,
    )

__all__ = (
    "wire",
    "unwire",
    "inject",
    "as_int",
    "as_float",
    "as_",
    "required",
    "invariant",
    "provided",
    "Provide",
    "Provider",
    "Closing",
    "register_loader_containers",
    "unregister_loader_containers",
    "install_loader",
    "uninstall_loader",
    "is_loader_installed",
)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
Container = Any


class PatchedRegistry:

    def __init__(self) -> None:
        self._callables: Dict[Callable[..., Any], "PatchedCallable"] = {}
        self._attributes: Set[PatchedAttribute] = set()

    def register_callable(self, patched: "PatchedCallable") -> None:
        self._callables[patched.patched] = patched

    def get_callables_from_module(self, module: ModuleType) -> Iterator[Callable[..., Any]]:
        for patched_callable in self._callables.values():
            if not patched_callable.is_in_module(module):
                continue
            yield patched_callable.patched

    def get_callable(self, fn: Callable[..., Any]) -> "PatchedCallable":
        return self._callables.get(fn)

    def has_callable(self, fn: Callable[..., Any]) -> bool:
        return fn in self._callables

    def register_attribute(self, patched: "PatchedAttribute") -> None:
        self._attributes.add(patched)

    def get_attributes_from_module(self, module: ModuleType) -> Iterator["PatchedAttribute"]:
        for attribute in self._attributes:
            if not attribute.is_in_module(module):
                continue
            yield attribute

    def clear_module_attributes(self, module: ModuleType) -> None:
        for attribute in self._attributes.copy():
            if not attribute.is_in_module(module):
                continue
            self._attributes.remove(attribute)


class PatchedCallable:

    __slots__ = (
        "patched",
        "original",
        "reference_injections",
        "injections",
        "reference_closing",
        "closing",
    )

    def __init__(
            self,
            patched: Optional[Callable[..., Any]] = None,
            original: Optional[Callable[..., Any]] = None,
            reference_injections: Optional[Dict[Any, Any]] = None,
            reference_closing: Optional[Dict[Any, Any]] = None,
    ) -> None:
        self.patched = patched
        self.original = original

        if reference_injections is None:
            reference_injections = {}
        self.reference_injections: Dict[Any, Any] = reference_injections.copy()
        self.injections: Dict[Any, Any] = {}

        if reference_closing is None:
            reference_closing = {}
        self.reference_closing: Dict[Any, Any] = reference_closing.copy()
        self.closing: Dict[Any, Any] = {}

    def is_in_module(self, module: ModuleType) -> bool:
        if self.patched is None:
            return False
        return self.patched.__module__ == module.__name__

    def add_injection(self, kwarg: Any, injection: Any) -> None:
        self.injections[kwarg] = injection

    def add_closing(self, kwarg: Any, injection: Any) -> None:
        self.closing[kwarg] = injection

    def unwind_injections(self) -> None:
        self.injections = {}
        self.closing = {}


class PatchedAttribute:

    __slots__ = (
        "member",
        "name",
        "marker",
    )

    def __init__(self, member: Any, name: str, marker: "_Marker") -> None:
        self.member = member
        self.name = name
        self.marker = marker

    @property
    def module_name(self) -> str:
        if isinstance(self.member, ModuleType):
            return self.member.__name__
        else:
            return self.member.__module__

    def is_in_module(self, module: ModuleType) -> bool:
        return self.module_name == module.__name__


class ProvidersMap:

    CONTAINER_STRING_ID = "<container>"

    def __init__(self, container) -> None:
        self._container = container
        self._map = self._create_providers_map(
            current_container=container,
            original_container=(
                container.declarative_parent
                if container.declarative_parent
                else container
            ),
        )

    def resolve_provider(
            self,
            provider: Union[providers.Provider, str],
            modifier: Optional["Modifier"] = None,
    ) -> Optional[providers.Provider]:
        if isinstance(provider, providers.Delegate):
            return self._resolve_delegate(provider)
        elif isinstance(provider, (
            providers.ProvidedInstance,
            providers.AttributeGetter,
            providers.ItemGetter,
            providers.MethodCaller,
        )):
            return self._resolve_provided_instance(provider)
        elif isinstance(provider, providers.ConfigurationOption):
            return self._resolve_config_option(provider)
        elif isinstance(provider, providers.TypedConfigurationOption):
            return self._resolve_config_option(provider.option, as_=provider.provides)
        elif isinstance(provider, str):
            return self._resolve_string_id(provider, modifier)
        else:
            return self._resolve_provider(provider)

    def _resolve_string_id(
            self,
            id: str,
            modifier: Optional["Modifier"] = None,
    ) -> Optional[providers.Provider]:
        if id == self.CONTAINER_STRING_ID:
            return self._container.__self__

        provider = self._container
        for segment in id.split("."):
            try:
                provider = getattr(provider, segment)
            except AttributeError:
                return None

        if modifier:
            provider = modifier.modify(provider, providers_map=self)
        return provider

    def _resolve_provided_instance(
            self,
            original: providers.Provider,
    ) -> Optional[providers.Provider]:
        modifiers = []
        while isinstance(original, (
                providers.ProvidedInstance,
                providers.AttributeGetter,
                providers.ItemGetter,
                providers.MethodCaller,
        )):
            modifiers.insert(0, original)
            original = original.provides

        new = self._resolve_provider(original)
        if new is None:
            return None

        for modifier in modifiers:
            if isinstance(modifier, providers.ProvidedInstance):
                new = new.provided
            elif isinstance(modifier, providers.AttributeGetter):
                new = getattr(new, modifier.name)
            elif isinstance(modifier, providers.ItemGetter):
                new = new[modifier.name]
            elif isinstance(modifier, providers.MethodCaller):
                new = new.call(
                    *modifier.args,
                    **modifier.kwargs,
                )

        return new

    def _resolve_delegate(
            self,
            original: providers.Delegate,
    ) -> Optional[providers.Provider]:
        provider = self._resolve_provider(original.provides)
        if provider:
            provider = provider.provider
        return provider

    def _resolve_config_option(
            self,
            original: providers.ConfigurationOption,
            as_: Any = None,
    ) -> Optional[providers.Provider]:
        original_root = original.root
        new = self._resolve_provider(original_root)
        if new is None:
            return None
        new = cast(providers.Configuration, new)

        for segment in original.get_name_segments():
            if providers.is_provider(segment):
                segment = self.resolve_provider(segment)
                new = new[segment]
            else:
                new = getattr(new, segment)

        if original.is_required():
            new = new.required()

        if as_:
            new = new.as_(as_)

        return new

    def _resolve_provider(
            self,
            original: providers.Provider,
    ) -> Optional[providers.Provider]:
        try:
            return self._map[original]
        except KeyError:
            return None

    @classmethod
    def _create_providers_map(
            cls,
            current_container: Container,
            original_container: Container,
    ) -> Dict[providers.Provider, providers.Provider]:
        current_providers = current_container.providers
        current_providers["__self__"] = current_container.__self__

        original_providers = original_container.providers
        original_providers["__self__"] = original_container.__self__

        providers_map = {}
        for provider_name, current_provider in current_providers.items():
            original_provider = original_providers[provider_name]
            providers_map[original_provider] = current_provider

            if isinstance(current_provider, providers.Container) \
                    and isinstance(original_provider, providers.Container):
                subcontainer_map = cls._create_providers_map(
                    current_container=current_provider.container,
                    original_container=original_provider.container,
                )
                providers_map.update(subcontainer_map)

        return providers_map


class InspectFilter:

    def is_excluded(self, instance: object) -> bool:
        if self._is_werkzeug_local_proxy(instance):
            return True
        elif self._is_starlette_request_cls(instance):
            return True
        elif self._is_builtin(instance):
            return True
        else:
            return False

    def _is_werkzeug_local_proxy(self, instance: object) -> bool:
        return werkzeug and isinstance(instance, werkzeug.local.LocalProxy)

    def _is_starlette_request_cls(self, instance: object) -> bool:
        return starlette \
               and isinstance(instance, type) \
               and _safe_is_subclass(instance, starlette.requests.Request)

    def _is_builtin(self, instance: object) -> bool:
        return inspect.isbuiltin(instance)


def wire(  # noqa: C901
        container: Container,
        *,
        modules: Optional[Iterable[ModuleType]] = None,
        packages: Optional[Iterable[ModuleType]] = None,
) -> None:
    """Wire container providers with provided packages and modules."""
    modules = [*modules] if modules else []

    if packages:
        for package in packages:
            modules.extend(_fetch_modules(package))

    providers_map = ProvidersMap(container)

    for module in modules:
        for member_name, member in inspect.getmembers(module):
            if _inspect_filter.is_excluded(member):
                continue

            if _is_marker(member):
                _patch_attribute(module, member_name, member, providers_map)
            elif inspect.isfunction(member):
                _patch_fn(module, member_name, member, providers_map)
            elif inspect.isclass(member):
                cls = member
                try:
                    cls_members = inspect.getmembers(cls)
                except Exception:  # noqa
                    # Hotfix, see: https://github.com/ets-labs/python-dependency-injector/issues/441
                    continue
                else:
                    for cls_member_name, cls_member in cls_members:
                        if _is_marker(cls_member):
                            _patch_attribute(cls, cls_member_name, cls_member, providers_map)
                        elif _is_method(cls_member):
                            _patch_method(cls, cls_member_name, cls_member, providers_map)

        for patched in _patched_registry.get_callables_from_module(module):
            _bind_injections(patched, providers_map)


def unwire(  # noqa: C901
        *,
        modules: Optional[Iterable[ModuleType]] = None,
        packages: Optional[Iterable[ModuleType]] = None,
) -> None:
    """Wire provided packages and modules with previous wired providers."""
    modules = [*modules] if modules else []

    if packages:
        for package in packages:
            modules.extend(_fetch_modules(package))

    for module in modules:
        for name, member in inspect.getmembers(module):
            if inspect.isfunction(member):
                _unpatch(module, name, member)
            elif inspect.isclass(member):
                for method_name, method in inspect.getmembers(member, inspect.isfunction):
                    _unpatch(member, method_name, method)

        for patched in _patched_registry.get_callables_from_module(module):
            _unbind_injections(patched)

        for patched_attribute in _patched_registry.get_attributes_from_module(module):
            _unpatch_attribute(patched_attribute)
        _patched_registry.clear_module_attributes(module)


def inject(fn: F) -> F:
    """Decorate callable with injecting decorator."""
    reference_injections, reference_closing = _fetch_reference_injections(fn)
    patched = _get_patched(fn, reference_injections, reference_closing)
    return cast(F, patched)


def _patch_fn(
        module: ModuleType,
        name: str,
        fn: Callable[..., Any],
        providers_map: ProvidersMap,
) -> None:
    if not _is_patched(fn):
        reference_injections, reference_closing = _fetch_reference_injections(fn)
        if not reference_injections:
            return
        fn = _get_patched(fn, reference_injections, reference_closing)

    _bind_injections(fn, providers_map)

    setattr(module, name, fn)


def _patch_method(
        cls: Type,
        name: str,
        method: Callable[..., Any],
        providers_map: ProvidersMap,
) -> None:
    if hasattr(cls, "__dict__") \
            and name in cls.__dict__ \
            and isinstance(cls.__dict__[name], (classmethod, staticmethod)):
        method = cls.__dict__[name]
        fn = method.__func__
    else:
        fn = method

    if not _is_patched(fn):
        reference_injections, reference_closing = _fetch_reference_injections(fn)
        if not reference_injections:
            return
        fn = _get_patched(fn, reference_injections, reference_closing)

    _bind_injections(fn, providers_map)

    if isinstance(method, (classmethod, staticmethod)):
        fn = type(method)(fn)

    setattr(cls, name, fn)


def _unpatch(
        module: ModuleType,
        name: str,
        fn: Callable[..., Any],
) -> None:
    if hasattr(module, "__dict__") \
            and name in module.__dict__ \
            and isinstance(module.__dict__[name], (classmethod, staticmethod)):
        method = module.__dict__[name]
        fn = method.__func__

    if not _is_patched(fn):
        return

    _unbind_injections(fn)


def _patch_attribute(
        member: Any,
        name: str,
        marker: "_Marker",
        providers_map: ProvidersMap,
) -> None:
    provider = providers_map.resolve_provider(marker.provider, marker.modifier)
    if provider is None:
        return

    _patched_registry.register_attribute(PatchedAttribute(member, name, marker))

    if isinstance(marker, Provide):
        instance = provider()
        setattr(member, name, instance)
    elif isinstance(marker, Provider):
        setattr(member, name, provider)
    else:
        raise Exception(f"Unknown type of marker {marker}")


def _unpatch_attribute(patched: PatchedAttribute) -> None:
    setattr(patched.member, patched.name, patched.marker)


def _fetch_reference_injections(  # noqa: C901
        fn: Callable[..., Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    # Hotfix, see:
    # - https://github.com/ets-labs/python-dependency-injector/issues/362
    # - https://github.com/ets-labs/python-dependency-injector/issues/398
    if GenericAlias and any((
                fn is GenericAlias,
                getattr(fn, "__func__", None) is GenericAlias
            )):
        fn = fn.__init__

    try:
        signature = inspect.signature(fn)
    except ValueError as exception:
        if "no signature found" in str(exception):
            return {}, {}
        elif "not supported by signature" in str(exception):
            return {}, {}
        else:
            raise exception

    injections = {}
    closing = {}
    for parameter_name, parameter in signature.parameters.items():
        if not isinstance(parameter.default, _Marker) \
                and not _is_fastapi_depends(parameter.default):
            continue

        marker = parameter.default

        if _is_fastapi_depends(marker):
            marker = marker.dependency

            if not isinstance(marker, _Marker):
                continue

        if isinstance(marker, Closing):
            marker = marker.provider
            closing[parameter_name] = marker

        injections[parameter_name] = marker
    return injections, closing


def _locate_dependent_closing_args(provider: providers.Provider) -> Dict[str, providers.Provider]:
    if not hasattr(provider, "args"):
        return {}

    closing_deps = {}
    for arg in provider.args:
        if not isinstance(arg, providers.Provider) or not hasattr(arg, "args"):
            continue

        if not arg.args and isinstance(arg, providers.Resource):
            return {str(id(arg)): arg}
        else:
            closing_deps += _locate_dependent_closing_args(arg)
    return closing_deps


def _bind_injections(fn: Callable[..., Any], providers_map: ProvidersMap) -> None:
    patched_callable = _patched_registry.get_callable(fn)
    if patched_callable is None:
        return

    for injection, marker in patched_callable.reference_injections.items():
        provider = providers_map.resolve_provider(marker.provider, marker.modifier)

        if provider is None:
            continue

        if isinstance(marker, Provide):
            patched_callable.add_injection(injection, provider)
        elif isinstance(marker, Provider):
            if isinstance(provider, providers.Delegate):
                patched_callable.add_injection(injection, provider)
            else:
                patched_callable.add_injection(injection, provider.provider)

        if injection in patched_callable.reference_closing:
            patched_callable.add_closing(injection, provider)
            deps = _locate_dependent_closing_args(provider)
            for key, dep in deps.items():
                patched_callable.add_closing(key, dep)


def _unbind_injections(fn: Callable[..., Any]) -> None:
    patched_callable = _patched_registry.get_callable(fn)
    if patched_callable is None:
        return
    patched_callable.unwind_injections()


def _fetch_modules(package):
    modules = [package]
    if not hasattr(package, "__path__") or not hasattr(package, "__name__"):
        return modules
    for module_info in pkgutil.walk_packages(
            path=package.__path__,
            prefix=package.__name__ + ".",
    ):
        module = importlib.import_module(module_info.name)
        modules.append(module)
    return modules


def _is_method(member) -> bool:
    return inspect.ismethod(member) or inspect.isfunction(member)


def _is_marker(member) -> bool:
    return isinstance(member, _Marker)


def _get_patched(
        fn: F,
        reference_injections: Dict[Any, Any],
        reference_closing: Dict[Any, Any],
) -> F:
    patched_object = PatchedCallable(
        original=fn,
        reference_injections=reference_injections,
        reference_closing=reference_closing,
    )

    if inspect.iscoroutinefunction(fn):
        patched = _get_async_patched(fn, patched_object)
    else:
        patched = _get_sync_patched(fn, patched_object)

    patched_object.patched = patched
    _patched_registry.register_callable(patched_object)

    return patched


def _is_fastapi_depends(param: Any) -> bool:
    return fastapi and isinstance(param, fastapi.params.Depends)


def _is_patched(fn) -> bool:
    return _patched_registry.has_callable(fn)


def _is_declarative_container(instance: Any) -> bool:
    return (isinstance(instance, type)
            and getattr(instance, "__IS_CONTAINER__", False) is True
            and getattr(instance, "declarative_parent", None) is None)


def _safe_is_subclass(instance: Any, cls: Type) -> bool:
    try:
        return issubclass(instance, cls)
    except TypeError:
        return False


class Modifier:

    def modify(
            self,
            provider: providers.ConfigurationOption,
            providers_map: ProvidersMap,
    ) -> providers.Provider:
        ...


class TypeModifier(Modifier):

    def __init__(self, type_: Type) -> None:
        self.type_ = type_

    def modify(
            self,
            provider: providers.ConfigurationOption,
            providers_map: ProvidersMap,
    ) -> providers.Provider:
        return provider.as_(self.type_)


def as_int() -> TypeModifier:
    """Return int type modifier."""
    return TypeModifier(int)


def as_float() -> TypeModifier:
    """Return float type modifier."""
    return TypeModifier(float)


def as_(type_: Type) -> TypeModifier:
    """Return custom type modifier."""
    return TypeModifier(type_)


class RequiredModifier(Modifier):

    def __init__(self) -> None:
        self.type_modifier = None

    def as_int(self) -> "RequiredModifier":
        self.type_modifier = TypeModifier(int)
        return self

    def as_float(self) -> "RequiredModifier":
        self.type_modifier = TypeModifier(float)
        return self

    def as_(self, type_: Type) -> "RequiredModifier":
        self.type_modifier = TypeModifier(type_)
        return self

    def modify(
            self,
            provider: providers.ConfigurationOption,
            providers_map: ProvidersMap,
    ) -> providers.Provider:
        provider = provider.required()
        if self.type_modifier:
            provider = provider.as_(self.type_modifier.type_)
        return provider


def required() -> RequiredModifier:
    """Return required modifier."""
    return RequiredModifier()


class InvariantModifier(Modifier):

    def __init__(self, id: str) -> None:
        self.id = id

    def modify(
            self,
            provider: providers.ConfigurationOption,
            providers_map: ProvidersMap,
    ) -> providers.Provider:
        invariant_segment = providers_map.resolve_provider(self.id)
        return provider[invariant_segment]


def invariant(id: str) -> InvariantModifier:
    """Return invariant modifier."""
    return InvariantModifier(id)


class ProvidedInstance(Modifier):

    TYPE_ATTRIBUTE = "attr"
    TYPE_ITEM = "item"
    TYPE_CALL = "call"

    def __init__(self) -> None:
        self.segments = []

    def __getattr__(self, item):
        self.segments.append((self.TYPE_ATTRIBUTE, item))
        return self

    def __getitem__(self, item):
        self.segments.append((self.TYPE_ITEM, item))
        return self

    def call(self):
        self.segments.append((self.TYPE_CALL, None))
        return self

    def modify(
            self,
            provider: providers.Provider,
            providers_map: ProvidersMap,
    ) -> providers.Provider:
        provider = provider.provided
        for type_, value in self.segments:
            if type_ == ProvidedInstance.TYPE_ATTRIBUTE:
                provider = getattr(provider, value)
            elif type_ == ProvidedInstance.TYPE_ITEM:
                provider = provider[value]
            elif type_ == ProvidedInstance.TYPE_CALL:
                provider = provider.call()
        return provider


def provided() -> ProvidedInstance:
    """Return provided instance modifier."""
    return ProvidedInstance()


class ClassGetItemMeta(GenericMeta):
    def __getitem__(cls, item):
        # Spike for Python 3.6
        if isinstance(item, tuple):
            return cls(*item)
        return cls(item)


class _Marker(Generic[T], metaclass=ClassGetItemMeta):

    __IS_MARKER__ = True

    def __init__(
            self,
            provider: Union[providers.Provider, Container, str],
            modifier: Optional[Modifier] = None,
    ) -> None:
        if _is_declarative_container(provider):
            provider = provider.__self__
        self.provider = provider
        self.modifier = modifier

    def __class_getitem__(cls, item) -> T:
        if isinstance(item, tuple):
            return cls(*item)
        return cls(item)

    def __call__(self) -> T:
        return self


class Provide(_Marker):
    ...


class Provider(_Marker):
    ...


class Closing(_Marker):
    ...


class AutoLoader:
    """Auto-wiring module loader.

    Automatically wire containers when modules are imported.
    """

    def __init__(self) -> None:
        self.containers = []
        self._path_hook = None

    def register_containers(self, *containers) -> None:
        self.containers.extend(containers)

        if not self.installed:
            self.install()

    def unregister_containers(self, *containers) -> None:
        for container in containers:
            self.containers.remove(container)

        if not self.containers:
            self.uninstall()

    def wire_module(self, module) -> None:
        for container in self.containers:
            container.wire(modules=[module])

    @property
    def installed(self) -> bool:
        return self._path_hook in sys.path_hooks

    def install(self) -> None:
        if self.installed:
            return

        loader = self

        class SourcelessFileLoader(importlib.machinery.SourcelessFileLoader):
            def exec_module(self, module):
                super().exec_module(module)
                loader.wire_module(module)

        class SourceFileLoader(importlib.machinery.SourceFileLoader):
            def exec_module(self, module):
                super().exec_module(module)
                loader.wire_module(module)

        class ExtensionFileLoader(importlib.machinery.ExtensionFileLoader):
            ...

        loader_details = [
            (SourcelessFileLoader, importlib.machinery.BYTECODE_SUFFIXES),
            (SourceFileLoader, importlib.machinery.SOURCE_SUFFIXES),
            (ExtensionFileLoader, importlib.machinery.EXTENSION_SUFFIXES),
        ]

        self._path_hook = importlib.machinery.FileFinder.path_hook(*loader_details)

        sys.path_hooks.insert(0, self._path_hook)
        sys.path_importer_cache.clear()
        importlib.invalidate_caches()

    def uninstall(self) -> None:
        if not self.installed:
            return

        sys.path_hooks.remove(self._path_hook)
        sys.path_importer_cache.clear()
        importlib.invalidate_caches()


def register_loader_containers(*containers: Container) -> None:
    """Register containers in auto-wiring module loader."""
    _loader.register_containers(*containers)


def unregister_loader_containers(*containers: Container) -> None:
    """Unregister containers from auto-wiring module loader."""
    _loader.unregister_containers(*containers)


def install_loader() -> None:
    """Install auto-wiring module loader hook."""
    _loader.install()


def uninstall_loader() -> None:
    """Uninstall auto-wiring module loader hook."""
    _loader.uninstall()


def is_loader_installed() -> bool:
    """Check if auto-wiring module loader hook is installed."""
    return _loader.installed


_patched_registry = PatchedRegistry()
_inspect_filter = InspectFilter()
_loader = AutoLoader()

# Optimizations
from ._cwiring import _sync_inject  # noqa
from ._cwiring import _async_inject  # noqa


# Wiring uses the following Python wrapper because there is
# no possibility to compile a first-type citizen coroutine in Cython.
def _get_async_patched(fn: F, patched: PatchedCallable) -> F:
    @functools.wraps(fn)
    async def _patched(*args, **kwargs):
        return await _async_inject(
            fn,
            args,
            kwargs,
            patched.injections,
            patched.closing,
        )
    return _patched

def _get_sync_patched(fn: F, patched: PatchedCallable) -> F:
    @functools.wraps(fn)
    def _patched(*args, **kwargs):
        return _sync_inject(
            fn,
            args,
            kwargs,
            patched.injections,
            patched.closing,
        )
    return _patched
