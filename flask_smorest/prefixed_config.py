from collections.abc import Mapping


class PrefixedConfigProxy(Mapping):
    def __init__(self, app, config_prefix):
        self._app = app
        self.config_prefix = config_prefix

    def __getitem__(self, key):
        return self._app.config[self.config_prefix + str(key)]

    def __iter__(self):
        return iter(x for x in self._app.config if x.startswith(self.config_prefix))

    def __len__(self):
        return sum(1 for _x in iter(self))
