import pytest

from .mocks import create_app_mock, AppConfig


@pytest.fixture(params=[AppConfig])
def app_mock(request):
    config_cls = request.param
    return create_app_mock(config_cls)
