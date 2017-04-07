import pytest

from .mocks import AppConfig, create_app_mock


@pytest.fixture(params=[{'app_config': AppConfig}])
def app_mock(request):
    params = request.param
    config_cls = params['app_config']
    as_method_view = params.get('app_as_method_view', True)
    return create_app_mock(config_cls, as_method_view=as_method_view)
