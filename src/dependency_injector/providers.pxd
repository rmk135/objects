"""Providers module."""

try:
    import asyncio
except ImportError:
    asyncio = None

import functools

cimport cython


cdef int ASYNC_MODE_UNDEFINED
cdef int ASYNC_MODE_ENABLED
cdef int ASYNC_MODE_DISABLED

cdef set __iscoroutine_typecache
cdef tuple __COROUTINE_TYPES


# Base providers
cdef class Provider(object):
    cdef tuple _overridden
    cdef Provider _last_overriding
    cdef tuple _overrides
    cdef int _async_mode

    cpdef bint is_async_mode_enabled(self)
    cpdef bint is_async_mode_disabled(self)
    cpdef bint is_async_mode_undefined(self)

    cpdef object _provide(self, tuple args, dict kwargs)
    cpdef void _copy_overridings(self, Provider copied, dict memo)


cdef class Object(Provider):
    cdef object _provides

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class Self(Provider):
    cdef object _container
    cdef tuple _alt_names


cdef class Delegate(Provider):
    cdef object _provides

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class Aggregate(Provider):
    cdef dict _providers

    cdef Provider __get_provider(self, object provider_name)


cdef class Dependency(Provider):
    cdef object _instance_of
    cdef object _default
    cdef object _parent


cdef class ExternalDependency(Dependency):
    pass


cdef class DependenciesContainer(Object):
    cdef dict _providers
    cdef object _parent

    cpdef object _override_providers(self, object container)


# Callable providers
cdef class Callable(Provider):
    cdef object _provides

    cdef tuple _args
    cdef int _args_len

    cdef tuple _kwargs
    cdef int _kwargs_len

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class DelegatedCallable(Callable):
    pass


cdef class AbstractCallable(Callable):
    cpdef object _provide(self, tuple args, dict kwargs)


cdef class CallableDelegate(Delegate):
    pass


# Coroutine providers
cdef class Coroutine(Callable):
    pass


cdef class DelegatedCoroutine(Coroutine):
    pass


cdef class AbstractCoroutine(Coroutine):
    cpdef object _provide(self, tuple args, dict kwargs)


cdef class CoroutineDelegate(Delegate):
    pass


# Configuration providers
cdef class ConfigurationOption(Provider):
    cdef tuple _name
    cdef Configuration _root
    cdef dict _children
    cdef bint _required
    cdef object _cache


cdef class TypedConfigurationOption(Callable):
    pass


cdef class Configuration(Object):
    cdef str _name
    cdef bint __strict
    cdef dict _children
    cdef list _ini_files
    cdef list _yaml_files
    cdef list _json_files
    cdef list _pydantic_settings
    cdef object __weakref__


# Factory providers
cdef class Factory(Provider):
    cdef Callable _instantiator

    cdef tuple _attributes
    cdef int _attributes_len

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class DelegatedFactory(Factory):
    pass


cdef class AbstractFactory(Factory):
    cpdef object _provide(self, tuple args, dict kwargs)


cdef class FactoryDelegate(Delegate):
    pass


cdef class FactoryAggregate(Aggregate):
    pass


# Singleton providers
cdef class BaseSingleton(Provider):
    cdef Factory _instantiator
    cdef object _storage


cdef class Singleton(BaseSingleton):

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class DelegatedSingleton(Singleton):
    pass


cdef class ThreadSafeSingleton(BaseSingleton):
    cdef object _storage_lock

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class DelegatedThreadSafeSingleton(ThreadSafeSingleton):
    pass


cdef class ThreadLocalSingleton(BaseSingleton):

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class ContextLocalSingleton(BaseSingleton):

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class DelegatedThreadLocalSingleton(ThreadLocalSingleton):
    pass


cdef class AbstractSingleton(BaseSingleton):
    pass


cdef class SingletonDelegate(Delegate):
    pass


# Miscellaneous providers

cdef class List(Provider):
    cdef tuple _args
    cdef int _args_len

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class Dict(Provider):
    cdef tuple _kwargs
    cdef int _kwargs_len

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class Resource(Provider):
    cdef object _provides
    cdef bint _initialized
    cdef object _shutdowner
    cdef object _resource

    cdef tuple _args
    cdef int _args_len

    cdef tuple _kwargs
    cdef int _kwargs_len

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class Container(Provider):
    cdef object _container_cls
    cdef dict _overriding_providers
    cdef object _container
    cdef object _parent

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class Selector(Provider):
    cdef object _selector
    cdef dict _providers

    cpdef object _provide(self, tuple args, dict kwargs)

# Provided instance

cdef class ProvidedInstance(Provider):
    cdef object _provides

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class AttributeGetter(Provider):
    cdef object _provides
    cdef object _name

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class ItemGetter(Provider):
    cdef object _provides
    cdef object _name

    cpdef object _provide(self, tuple args, dict kwargs)


cdef class MethodCaller(Provider):
    cdef object _provides
    cdef tuple _args
    cdef int _args_len
    cdef tuple _kwargs
    cdef int _kwargs_len

    cpdef object _provide(self, tuple args, dict kwargs)


# Injections
cdef class Injection(object):
    cdef object _value
    cdef int _is_provider
    cdef int _is_delegated
    cdef int _call


cdef class PositionalInjection(Injection):
    pass


cdef class NamedInjection(Injection):
    cdef object _name


cpdef tuple parse_positional_injections(tuple args)


cpdef tuple parse_named_injections(dict kwargs)


# Utils
cdef class OverridingContext(object):
    cdef Provider _overridden
    cdef Provider _overriding


cdef class BaseSingletonResetContext(object):
    cdef object _singleton


cdef class SingletonResetContext(BaseSingletonResetContext):
    pass


cdef class SingletonFullResetContext(BaseSingletonResetContext):
    pass


cdef object CLASS_TYPES


cpdef bint is_provider(object instance)


cpdef object ensure_is_provider(object instance)


cpdef bint is_delegated(object instance)


cpdef str represent_provider(object provider, object provides)


cpdef bint is_container_instance(object instance)


cpdef bint is_container_class(object instance)


cpdef object deepcopy(object instance, dict memo=*)


# Inline helper functions
cdef inline object __get_name(NamedInjection self):
    return self._name


cdef inline object __get_value(Injection self):
    if self._call == 0:
        return self._value
    return self._value()


cdef inline object __get_value_kwargs(Injection self, dict kwargs):
    if self._call == 0:
        return self._value
    return self._value(**kwargs)


cdef inline tuple __separate_prefixed_kwargs(dict kwargs):
    cdef dict plain_kwargs = {}
    cdef dict prefixed_kwargs = {}

    for key, value in kwargs.items():
        if "__" not in key:
            plain_kwargs[key] = value
            continue

        index = key.index("__")
        prefix, name = key[:index], key[index+2:]

        if prefix not in prefixed_kwargs:
            prefixed_kwargs[prefix] = {}
        prefixed_kwargs[prefix][name] = value

    return plain_kwargs, prefixed_kwargs


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline object __provide_positional_args(
        tuple args,
        tuple inj_args,
        int inj_args_len,
        int async_mode,
):
    cdef int index
    cdef list positional_args = []
    cdef list future_args = []
    cdef PositionalInjection injection
    cdef object value

    if inj_args_len == 0:
        return args

    for index in range(inj_args_len):
        injection = <PositionalInjection>inj_args[index]
        value = __get_value(injection)
        positional_args.append(value)

        if async_mode != ASYNC_MODE_DISABLED and __is_future_or_coroutine(value):
            future_args.append((index, value))

    positional_args.extend(args)

    if future_args:
        return __combine_future_injections(positional_args, future_args)

    return positional_args


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline object __provide_keyword_args(
        dict kwargs,
        tuple inj_kwargs,
        int inj_kwargs_len,
        int async_mode,
):
    cdef int index
    cdef object name
    cdef object value
    cdef dict prefixed = {}
    cdef list future_kwargs = []
    cdef NamedInjection kw_injection

    if len(kwargs) == 0:
        for index in range(inj_kwargs_len):
            kw_injection = <NamedInjection>inj_kwargs[index]
            name = __get_name(kw_injection)
            value = __get_value(kw_injection)
            kwargs[name] = value
            if async_mode != ASYNC_MODE_DISABLED and __is_future_or_coroutine(value):
                future_kwargs.append((name, value))
    else:
        kwargs, prefixed = __separate_prefixed_kwargs(kwargs)


        for index in range(inj_kwargs_len):
            kw_injection = <NamedInjection>inj_kwargs[index]
            name = __get_name(kw_injection)

            if name in kwargs:
                continue

            if name in prefixed:
                value = __get_value_kwargs(kw_injection, prefixed[name])
            else:
                value = __get_value(kw_injection)

            kwargs[name] = value
            if async_mode != ASYNC_MODE_DISABLED and __is_future_or_coroutine(value):
                future_kwargs.append((name, value))

    if future_kwargs:
        return __combine_future_injections(kwargs, future_kwargs)

    return kwargs


cdef inline object __combine_future_injections(object injections, list future_injections):
    future_result = asyncio.Future()

    injections_ready = asyncio.gather(*[value for _, value in future_injections])
    injections_ready.add_done_callback(
        functools.partial(
            __async_prepare_args_kwargs_callback,
            future_result,
            injections,
            future_injections,
        ),
    )
    asyncio.ensure_future(injections_ready)

    return future_result


cdef inline void __async_prepare_args_kwargs_callback(
        object future_result,
        object args,
        object future_args_kwargs,
        object future,
):
    try:
        result = future.result()
        for value, (key, _) in zip(result, future_args_kwargs):
            args[key] = value
    except Exception as exception:
        exception.__traceback__.tb_frame.f_locals.clear()
        exception.__traceback__.tb_frame.f_locals.update(locals())
        future_result.set_exception(exception)
    else:
        future_result.set_result(args)


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline object __provide_attributes(tuple attributes, int attributes_len):
    cdef NamedInjection attr_injection
    cdef dict attribute_injections = {}
    cdef list future_attributes = []

    for index in range(attributes_len):
        attr_injection = <NamedInjection>attributes[index]
        name = __get_name(attr_injection)
        value = __get_value(attr_injection)
        attribute_injections[name] = value
        if __is_future_or_coroutine(value):
            future_attributes.append((name, value))

    if future_attributes:
        return __combine_future_injections(attribute_injections, future_attributes)

    return attribute_injections


cdef inline object __async_inject_attributes(future_instance, future_attributes):
    future_result = asyncio.Future()

    attributes_ready = asyncio.gather(future_instance, future_attributes)
    attributes_ready.add_done_callback(
        functools.partial(
            __async_inject_attributes_callback,
            future_result,
        ),
    )
    asyncio.ensure_future(attributes_ready)

    return future_result


cdef inline void __async_inject_attributes_callback(object future_result, object future):
    try:
        instance, attributes = future.result()

        for name, value in attributes.items():
            setattr(instance, name, value)
    except Exception as exception:
        exception.__traceback__.tb_frame.f_locals.clear()
        exception.__traceback__.tb_frame.f_locals.update(locals())
        future_result.set_exception(exception)
    else:
        future_result.set_result(instance)


cdef inline void __inject_attributes(object instance, dict attributes):
    for name, value in attributes.items():
        setattr(instance, name, value)


cdef inline object __call(
        object call,
        tuple context_args,
        tuple injection_args,
        int injection_args_len,
        dict context_kwargs,
        tuple injection_kwargs,
        int injection_kwargs_len,
        int async_mode,
):
    cdef object args = __provide_positional_args(
        context_args,
        injection_args,
        injection_args_len,
        async_mode,
    )
    cdef object kwargs = __provide_keyword_args(
        context_kwargs,
        injection_kwargs,
        injection_kwargs_len,
        async_mode,
    )

    if async_mode == ASYNC_MODE_DISABLED:
        return call(*args, **kwargs)

    cdef bint is_future_args = __is_future_or_coroutine(args)
    cdef bint is_future_kwargs = __is_future_or_coroutine(kwargs)

    if is_future_args or is_future_kwargs:
        future_args = args if is_future_args else __future_result(args)
        future_kwargs = kwargs if is_future_kwargs else __future_result(kwargs)

        future_result = asyncio.Future()

        args_kwargs_ready = asyncio.gather(future_args, future_kwargs)
        args_kwargs_ready.add_done_callback(
            functools.partial(
                __async_call_callback,
                future_result,
                call,
            ),
        )
        asyncio.ensure_future(args_kwargs_ready)

        return future_result
    try:
        return call(*args, **kwargs)
    except Exception as exception:
        exception.__traceback__.tb_frame.f_locals.clear()
        exception.__traceback__.tb_frame.f_locals.update(locals())
        raise exception

cdef inline void __async_call_callback(object future_result, object call, object future):
    try:
        args, kwargs = future.result()
        result = call(*args, **kwargs)
    except Exception as exception:
        exception.__traceback__.tb_frame.f_locals.clear()
        exception.__traceback__.tb_frame.f_locals.update(locals())
        future_result.set_exception(exception)
    else:
        if __is_future_or_coroutine(result):
            result = asyncio.ensure_future(result)
            result.add_done_callback(functools.partial(__async_result_callback, future_result))
            return
        future_result.set_result(result)


cdef inline object __async_result_callback(object future_result, object future):
    try:
        result = future.result()
    except Exception as exception:
        exception.__traceback__.tb_frame.f_locals.clear()
        exception.__traceback__.tb_frame.f_locals.update(locals())
        future_result.set_exception(exception)
    else:
        future_result.set_result(result)


cdef inline object __callable_call(Callable self, tuple args, dict kwargs, ):
    return __call(
        self._provides,
        args,
        self._args,
        self._args_len,
        kwargs,
        self._kwargs,
        self._kwargs_len,
        self._async_mode,
    )


cdef inline object __factory_call(Factory self, tuple args, dict kwargs):
    cdef object instance

    instance = __call(
        self._instantiator._provides,
        args,
        self._instantiator._args,
        self._instantiator._args_len,
        kwargs,
        self._instantiator._kwargs,
        self._instantiator._kwargs_len,
        self._async_mode,
    )

    if self._attributes_len > 0:
        attributes = __provide_attributes(self._attributes, self._attributes_len)

        is_future_instance = __is_future_or_coroutine(instance)
        is_future_attributes = __is_future_or_coroutine(attributes)

        if is_future_instance or is_future_attributes:
            future_instance = instance if is_future_instance else __future_result(instance)
            future_attributes = attributes if is_future_attributes else __future_result(attributes)
            return __async_inject_attributes(future_instance, future_attributes)

        __inject_attributes(instance, attributes)

    return instance


cdef inline bint __is_future_or_coroutine(object instance):
    return __isfuture(instance) or __iscoroutine(instance)


cdef inline bint __isfuture(object obj):
    return hasattr(obj.__class__, "_asyncio_future_blocking") and obj._asyncio_future_blocking is not None


cdef inline bint __iscoroutine(object obj):
    if type(obj) in __iscoroutine_typecache:
        return True

    if isinstance(obj, __COROUTINE_TYPES):
        # Just in case we don't want to cache more than 100
        # positive types.  That shouldn't ever happen, unless
        # someone stressing the system on purpose.
        if len(__iscoroutine_typecache) < 100:
            __iscoroutine_typecache.add(type(obj))
        return True
    else:
        return False


cdef inline object __future_result(object instance):
    future_result = asyncio.Future()
    future_result.set_result(instance)
    return future_result
