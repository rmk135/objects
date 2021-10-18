"""Configuration.from_yaml() tests."""

from dependency_injector import providers, errors
from pytest import fixture, mark, raises


@fixture
def config_file_1(tmp_path):
    config_file = str(tmp_path / "config_1.ini")
    with open(config_file, "w") as file:
        file.write(
            "section1:\n"
            "  value1: 1\n"
            "\n"
            "section2:\n"
            "  value2: 2\n"
        )
    return config_file


@fixture
def config_file_2(tmp_path):
    config_file = str(tmp_path / "config_2.ini")
    with open(config_file, "w") as file:
        file.write(
            "section1:\n"
            "  value1: 11\n"
            "  value11: 11\n"
            "section3:\n"
            "  value3: 3\n"
        )
    return config_file


@fixture
def no_yaml_module_installed():
    yaml = providers.yaml
    providers.yaml = None
    yield
    providers.yaml = yaml


def test(config, config_file_1):
    config.from_yaml(config_file_1)

    assert config() == {"section1": {"value1": 1}, "section2": {"value2": 2}}
    assert config.section1() == {"value1": 1}
    assert config.section1.value1() == 1
    assert config.section2() == {"value2": 2}
    assert config.section2.value2() == 2


def test_merge(config, config_file_1, config_file_2):
    config.from_yaml(config_file_1)
    config.from_yaml(config_file_2)

    assert config() == {
        "section1": {
            "value1": 11,
            "value11": 11,
        },
        "section2": {
            "value2": 2,
        },
        "section3": {
            "value3": 3,
        },
    }
    assert config.section1() == {"value1": 11, "value11": 11}
    assert config.section1.value1() == 11
    assert config.section1.value11() == 11
    assert config.section2() == {"value2": 2}
    assert config.section2.value2() == 2
    assert config.section3() == {"value3": 3}
    assert config.section3.value3() == 3


def test_file_does_not_exist(config):
    config.from_yaml("./does_not_exist.yml")
    assert config() == {}


@mark.parametrize("config_type", ["strict"])
def test_file_does_not_exist_strict_mode(config):
    with raises(IOError):
        config.from_yaml("./does_not_exist.yml")


def test_option_file_does_not_exist(config):
    config.option.from_yaml("./does_not_exist.yml")
    assert config.option() is None


@mark.parametrize("config_type", ["strict"])
def test_option_file_does_not_exist_strict_mode(config):
    with raises(IOError):
        config.option.from_yaml("./does_not_exist.yml")


def test_required_file_does_not_exist(config):
    with raises(IOError):
        config.from_yaml("./does_not_exist.yml", required=True)


def test_required_option_file_does_not_exist(config):
    with raises(IOError):
        config.option.from_yaml("./does_not_exist.yml", required=True)


@mark.parametrize("config_type", ["strict"])
def test_not_required_file_does_not_exist_strict_mode(config):
    config.from_yaml("./does_not_exist.yml", required=False)
    assert config() == {}


@mark.parametrize("config_type", ["strict"])
def test_not_required_option_file_does_not_exist_strict_mode(config):
    config.option.from_yaml("./does_not_exist.yml", required=False)
    with raises(errors.Error):
        config.option()


@mark.usefixtures("no_yaml_module_installed")
def test_no_yaml_installed(config, config_file_1):
    with raises(errors.Error) as error:
        config.from_yaml(config_file_1)
    assert error.value.args[0] == (
        "Unable to load yaml configuration - PyYAML is not installed. "
        "Install PyYAML or install Dependency Injector with yaml extras: "
        "\"pip install dependency-injector[yaml]\""
    )


@mark.usefixtures("no_yaml_module_installed")
def test_option_no_yaml_installed(config, config_file_1):
    with raises(errors.Error) as error:
        config.option.from_yaml(config_file_1)
    assert error.value.args[0] == (
        "Unable to load yaml configuration - PyYAML is not installed. "
        "Install PyYAML or install Dependency Injector with yaml extras: "
        "\"pip install dependency-injector[yaml]\""
    )
