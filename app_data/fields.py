from copy import copy

from django.utils import simplejson as json

from south.modelsinspector import add_introspection_rules

from jsonfield.fields import JSONField

from .registry import app_registry


class AppDataField(JSONField):
    def __init__(self, *args, **kwargs):
        self.app_registry = kwargs.pop('app_registry', app_registry)
        kwargs.setdefault('default', '{}')
        kwargs.setdefault('editable', False)
        super(AppDataField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """Convert string value to JSON and wrap it in AppDataContainerFactory"""
        if isinstance(value, basestring):
            try:
                val = json.loads(value)
                return AppDataContainerFactory(self.model, val, app_registry=self.app_registry)
            except ValueError:
                pass

        # app_data = {} should use AppDataContainerFactory
        if isinstance(value, dict) and not isinstance(value, AppDataContainerFactory):
            value = AppDataContainerFactory(self.model, value, app_registry=self.app_registry)

        return value

    def validate(self, value, model_instance):
        super(AppDataField, self).validate(value, model_instance)
        for k in value:
            data = value[k]
            if hasattr(data, 'validate'):
                data.validate(value, model_instance)


add_introspection_rules([], ["^app_data\.fields\.AppDataField"])


class AppDataContainerFactory(dict):
    def __init__(self, model, *args, **kwargs):
        self._model = model
        self._app_registry = kwargs.pop('app_registry', app_registry)
        super(AppDataContainerFactory, self).__init__(*args, **kwargs)

    def __setattr__(self, name, value):
        if name.startswith('_') or self._app_registry.get_class(name, self._model) is None:
            super(AppDataContainerFactory, self).__setattr__(name, value)
        else:
            self[name] = copy(value)

    def __getattr__(self, name):
        if name.startswith('_') or self._app_registry.get_class(name, self._model) is None:
            raise AttributeError()
        return self[name]

    def __getitem__(self, name):
        class_ = self._app_registry.get_class(name, self._model)
        try:
            val = super(AppDataContainerFactory, self).__getitem__(name)
        except KeyError:
            if class_ is None:
                raise
            val = class_()
            self[name] = val
        else:
            if class_ is not None and not isinstance(val, class_):
                val = class_(val)
                self[name] = val

        return val

    def get(self, name, default=None):
        if name in self:
            return self[name]

        if default is None:
            return None

        class_ = self._app_registry.get_class(name, self._model)
        if class_ is not None and not isinstance(default, class_):
            return class_(default)

        return default
