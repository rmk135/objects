"""Main wiring tests."""

from decimal import Decimal

from dependency_injector import errors
from dependency_injector.wiring import Closing, Provide, Provider, wire
from pytest import fixture, mark, raises

from samples.wiringstringids import module, package, resourceclosing
from samples.wiringstringids.service import Service
from samples.wiringstringids.container import Container, SubContainer


@fixture(autouse=True)
def container():
    container = Container(config={"a": {"b": {"c": 10}}})
    container.wire(
        modules=[module],
        packages=[package],
    )
    yield container
    container.unwire()


@fixture
def subcontainer():
    container = SubContainer()
    container.wire(
        modules=[module],
        packages=[package],
    )
    yield container
    container.unwire()


@fixture(params=[
    resourceclosing.Container,
    resourceclosing.ContainerSingleton,
])
def resourceclosing_container(request):
    container = request.param()
    container.wire(modules=[resourceclosing])
    yield container
    container.unwire()


def test_package_lookup():
    from samples.wiringstringids.package import test_package_function
    service = test_package_function()
    assert isinstance(service, Service)


def test_package_subpackage_lookup():
    from samples.wiringstringids.package.subpackage import test_package_function
    service = test_package_function()
    assert isinstance(service, Service)


def test_package_submodule_lookup():
    from samples.wiringstringids.package.subpackage.submodule import test_function
    service = test_function()
    assert isinstance(service, Service)


def test_module_attributes_wiring():
    assert isinstance(module.service, Service)
    assert isinstance(module.service_provider(), Service)
    assert isinstance(module.undefined, Provide)


def test_module_attribute_wiring_with_invalid_marker(container: Container):
    from samples.wiringstringids import module_invalid_attr_injection
    with raises(Exception, match="Unknown type of marker {0}".format(module_invalid_attr_injection.service)):
        container.wire(modules=[module_invalid_attr_injection])


def test_class_wiring():
    test_class_object = module.TestClass()
    assert isinstance(test_class_object.service, Service)


def test_class_wiring_context_arg(container: Container):
    test_service = container.service()
    test_class_object = module.TestClass(service=test_service)
    assert test_class_object.service is test_service


def test_class_method_wiring():
    test_class_object = module.TestClass()
    service = test_class_object.method()
    assert isinstance(service, Service)


def test_class_classmethod_wiring():
    service = module.TestClass.class_method()
    assert isinstance(service, Service)


def test_instance_classmethod_wiring():
    instance = module.TestClass()
    service = instance.class_method()
    assert isinstance(service, Service)


def test_class_staticmethod_wiring():
    service = module.TestClass.static_method()
    assert isinstance(service, Service)


def test_instance_staticmethod_wiring():
    instance = module.TestClass()
    service = instance.static_method()
    assert isinstance(service, Service)


def test_class_attribute_wiring():
    assert isinstance(module.TestClass.service, Service)
    assert isinstance(module.TestClass.service_provider(), Service)
    assert isinstance(module.TestClass.undefined, Provide)


def test_function_wiring():
    service = module.test_function()
    assert isinstance(service, Service)


def test_function_wiring_context_arg(container: Container):
    test_service = container.service()
    service = module.test_function(service=test_service)
    assert service is test_service


def test_function_wiring_provider():
    service = module.test_function_provider()
    assert isinstance(service, Service)


def test_function_wiring_provider_context_arg(container: Container):
    test_service = container.service()
    service = module.test_function_provider(service_provider=lambda: test_service)
    assert service is test_service


def test_configuration_option():
    (
        value_int,
        value_float,
        value_str,
        value_decimal,
        value_required,
        value_required_int,
        value_required_float,
        value_required_str,
        value_required_decimal,
    ) = module.test_config_value()

    assert value_int == 10
    assert value_float == 10.0
    assert value_str == "10"
    assert value_decimal == Decimal(10)
    assert value_required == 10
    assert value_required_int == 10
    assert value_required_float == 10.0
    assert value_required_str == "10"
    assert value_required_decimal == Decimal(10)


def test_configuration_option_required_undefined(container: Container):
    container.config.reset_override()
    with raises(errors.Error, match="Undefined configuration option \"config.a.b.c\""):
        module.test_config_value_required_undefined()


def test_provide_provider():
    service = module.test_provide_provider()
    assert isinstance(service, Service)


def test_provider_provider():
    service = module.test_provider_provider()
    assert isinstance(service, Service)


def test_provided_instance(container: Container):
    class TestService:
        foo = {"bar": lambda: 10}

    with container.service.override(TestService()):
        some_value = module.test_provided_instance()
    assert some_value == 10


def test_subcontainer():
    some_value = module.test_subcontainer_provider()
    assert some_value == 1


def test_config_invariant(container: Container):
    config = {
        "option": {
            "a": 1,
            "b": 2,
        },
        "switch": "a",
    }
    container.config.from_dict(config)

    value_default = module.test_config_invariant()
    assert value_default == 1

    with container.config.switch.override("a"):
        value_a = module.test_config_invariant()
    assert value_a == 1

    with container.config.switch.override("b"):
        value_b = module.test_config_invariant()
    assert value_b == 2


def test_wire_with_class_error():
    with raises(Exception):
        wire(
            container=Container,
            modules=[module],
        )


def test_unwire_function(container: Container):
    container.unwire()
    assert isinstance(module.test_function(), Provide)


def test_unwire_class(container: Container):
    container.unwire()
    test_class_object = module.TestClass()
    assert isinstance(test_class_object.service, Provide)


def test_unwire_class_method(container: Container):
    container.unwire()
    test_class_object = module.TestClass()
    assert isinstance(test_class_object.method(), Provide)


def test_unwire_package_function(container: Container):
    container.unwire()
    from samples.wiringstringids.package.subpackage.submodule import test_function
    assert isinstance(test_function(), Provide)


def test_unwire_package_function_by_reference(container: Container):
    from samples.wiringstringids.package.subpackage import submodule
    container.unwire()
    assert isinstance(submodule.test_function(), Provide)


def test_unwire_module_attributes(container: Container):
    container.unwire()
    assert isinstance(module.service, Provide)
    assert isinstance(module.service_provider, Provider)
    assert isinstance(module.undefined, Provide)


def test_unwire_class_attributes(container: Container):
    container.unwire()
    assert isinstance(module.TestClass.service, Provide)
    assert isinstance(module.TestClass.service_provider, Provider)
    assert isinstance(module.TestClass.undefined, Provide)


@mark.usefixtures("subcontainer")
def test_wire_multiple_containers():
    service, some_value = module.test_provide_from_different_containers()
    assert isinstance(service, Service)
    assert some_value == 1


@mark.usefixtures("resourceclosing_container")
def test_closing_resource():
    resourceclosing.Service.reset_counter()

    result_1 = resourceclosing.test_function()
    assert isinstance(result_1, resourceclosing.Service)
    assert result_1.init_counter == 1
    assert result_1.shutdown_counter == 1

    result_2 = resourceclosing.test_function()
    assert isinstance(result_2, resourceclosing.Service)
    assert result_2.init_counter == 2
    assert result_2.shutdown_counter == 2

    assert result_1 is not result_2


@mark.usefixtures("resourceclosing_container")
def test_closing_dependency_resource():
    resourceclosing.Service.reset_counter()

    result_1 = resourceclosing.test_function_dependency()
    assert isinstance(result_1, resourceclosing.FactoryService)
    assert result_1.service.init_counter == 1
    assert result_1.service.shutdown_counter == 1

    result_2 = resourceclosing.test_function_dependency()
    assert isinstance(result_2, resourceclosing.FactoryService)
    assert result_2.service.init_counter == 2
    assert result_2.service.shutdown_counter == 2


@mark.usefixtures("resourceclosing_container")
def test_closing_dependency_resource_kwargs():
    resourceclosing.Service.reset_counter()

    result_1 = resourceclosing.test_function_dependency_kwargs()
    assert isinstance(result_1, resourceclosing.FactoryService)
    assert result_1.service.init_counter == 1
    assert result_1.service.shutdown_counter == 1

    result_2 = resourceclosing.test_function_dependency_kwargs()
    assert isinstance(result_2, resourceclosing.FactoryService)
    assert result_2.service.init_counter == 2
    assert result_2.service.shutdown_counter == 2


@mark.usefixtures("resourceclosing_container")
def test_closing_nested_dependency_resource():
    resourceclosing.Service.reset_counter()

    result_1 = resourceclosing.test_function_nested_dependency()
    assert isinstance(result_1, resourceclosing.NestedService)
    assert result_1.factory_service.service.init_counter == 1
    assert result_1.factory_service.service.shutdown_counter == 1

    result_2 = resourceclosing.test_function_nested_dependency()
    assert isinstance(result_2, resourceclosing.NestedService)
    assert result_2.factory_service.service.init_counter == 2
    assert result_2.factory_service.service.shutdown_counter == 2

    assert result_1 is not result_2


@mark.usefixtures("resourceclosing_container")
def test_closing_resource_bypass_marker_injection():
    resourceclosing.Service.reset_counter()

    result_1 = resourceclosing.test_function(service=Closing[Provide["service"]])
    assert isinstance(result_1, resourceclosing.Service)
    assert result_1.init_counter == 1
    assert result_1.shutdown_counter == 1

    result_2 = resourceclosing.test_function(service=Closing[Provide["service"]])
    assert isinstance(result_2, resourceclosing.Service)
    assert result_2.init_counter == 2
    assert result_2.shutdown_counter == 2

    assert result_1 is not result_2


@mark.usefixtures("resourceclosing_container")
def test_closing_resource_context():
    resourceclosing.Service.reset_counter()
    service = resourceclosing.Service()

    result_1 = resourceclosing.test_function(service=service)
    assert result_1 is service
    assert result_1.init_counter == 0
    assert result_1.shutdown_counter == 0

    result_2 = resourceclosing.test_function(service=service)
    assert result_2 is service
    assert result_2.init_counter == 0
    assert result_2.shutdown_counter == 0


def test_class_decorator():
    service = module.test_class_decorator()
    assert isinstance(service, Service)


def test_container():
    service = module.test_container()
    assert isinstance(service, Service)


def test_bypass_marker_injection():
    service = module.test_function(service=Provide["service"])
    assert isinstance(service, Service)
