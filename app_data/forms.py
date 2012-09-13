from operator import methodcaller

from django.forms.forms import BoundField, NON_FIELD_ERRORS, Form

class AppDataForm(Form):
    def __init__(self, app_container, data=None, files=None, fields=(), exclude=(), **kwargs):
        self.app_container = app_container
        super(AppDataForm, self).__init__(data, files, **kwargs)

        if fields or exclude:
            for f in self.fields.keys():
                if fields and f not in fields:
                    del self.fields[f]
                elif f in exclude:
                    del self.fields[f]

    def save(self):
        self.app_container.update(self.cleaned_data)

class MultiForm(object):
    def __init__(self, *args, **kwargs):
        self.model_form = self.ModelForm(*args, **kwargs)
        data = self.model_form.data
        files = self.model_form.files

        app_container = getattr(self.model_form.instance, self.app_data_field)

        self.app_forms = {}

        for label, label_opts in self.app_form_opts.iteritems():
            self.app_forms[label] = app_container[label].get_form(data, files, prefix=label, **label_opts)

    @classmethod
    def add_form(cls, label, form_options):
        cls.app_form_opts[label] = form_options

    @classmethod
    def remove_form(cls, label):
        if label in cls.app_form_opts:
            del cls.app_form_opts[label]

    # TODO: mock other API of form like base_fields etc.
    def __getitem__(self, name):

        # provide access to app.field as well
        app = None
        if '.' in name:
            app, field = name.split('.', 1)

        if app is None:
            form = self.model_form
        else:
            try:
                form = self.app_forms[app]
            except KeyError:
                raise KeyError('AppForm %r not found in MultiForm.' % name)

        try:
            field = form[field]
        except KeyError:
            raise KeyError('Field %r not found in Form %s' % (name, form))

        return BoundField(form, field, name)

    def is_valid(self):
        return self.model_form.is_valid() and all(map(methodcaller('is_valid'), self.app_forms.itervalues()))

    @property
    def errors(self):
        # combine all the errors
        _errors = self.model_form.errors.copy()
        for label, form in self.app_forms.iteritems():
            for k, v in form.errors.iteritems():
                if k == NON_FIELD_ERRORS:
                    _errors[k] = _errors.get(k, []).extend(v)
                else:
                    _errors['%s.%s' % (label, k)] = v
        return _errors

    def save(self, **kwargs):
        # save the app_data forms first
        for f in self.app_forms.values():
            f.save()
        # save the model itself
        return self.model_form.save(**kwargs)

def multiform_factory(model_form, app_data_field='app_data', name=None, **form_opts):
    name = name or '%sWithAppDataForm' % model_form._meta.model.__name__
    return type(
        name, (MultiForm, ),
        {'ModelForm': model_form, 'app_data_field': app_data_field, 'app_form_opts': form_opts}
    )
