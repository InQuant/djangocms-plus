import logging

from collections import OrderedDict
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from djangocms_frontend.fields import AttributesFormField
from djangocms_frontend.common.title import TitleField
from entangled.forms import EntangledModelForm, EntangledModelFormMixin

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.models import PlusItem


logger = logging.getLogger(__name__)


class DeserializeMixin:

    def deserialize(self):
        """
        Deserialize data from Json field into dict. Opposite of serialize function (see above)
        :return: Data
        :rtype: dict:
        """
        parsed_dict = OrderedDict()

        for field_name in self.declared_fields:
            value = self.data.get(field_name, None)

            field = self.declared_fields.get(field_name)
            if hasattr(field, "deserialize_field"):
                deserialize_field = getattr(field, "deserialize_field")
                if callable(deserialize_field):
                    try:
                        parsed_dict[field_name] = deserialize_field(value)
                    except ValidationError as e:
                        self._update_errors(e)
            else:
                parsed_dict[field_name] = value

        return parsed_dict


class PlusPluginForm(DeserializeMixin, EntangledModelForm):
    class Meta:
        model = PlusItem
        entangled_fields = {
            "config": []
        }

# StylePluginMixin form fields
# ----------------------------
#
def get_style_form_fields(style_config_key="", style_multiple=False):
    """
    Use together with StylePluginMixin, e.g.

    class MyCustomForm(PlusPluginForm):
        ...  # form defs

        STYLE_CHOICES = 'MY_CUSTOM_STYLES'
        plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)


    class MyCustomPlugin(StylePluginMixin, PlusPluginBase):
        name = _('My Custom')
        form = MyCustomForm
        render_template = 'custom/snippet.html'

    style_config_key should be a cmsplus_settings - key which holds the
    style choices, e.g.: ('c-text-white', 'Text White'), ...
    """
    style_choices = (
        ('', 'None'),
    )

    sc = getattr(cps, style_config_key, style_choices)
    if style_multiple:
        style_field = forms.MultipleChoiceField
    else:
        style_field = forms.ChoiceField

    return [
        TitleField(
            label=_("Title"),
            required=False,
            help_text=_(
                "Optional title of the plugin for easier identification. "
                "Its <code>title</code> attribute "
                "will only be set if the checkbox is selected."
            ),
        ),
        style_field(
            label=_('Style'), required=False, choices=sc,
            initial=sc[0][0], help_text=_('Extra CSS predefined style class for plugin.')
        ),
        AttributesFormField(
            label=_('Extra CSS'), required=False, initial='',
            help_text=_('Add extra (device specific) css key, values, e.g: margin or margin:md or transform:xl'))
    ]


class PlusStyleEntangledFormMixin(DeserializeMixin, EntangledModelFormMixin):

    attributes = AttributesFormField()

    class Meta:
        entangled_fields = {
            "config": ['attributes']
        }

    def __init_subclass__(cls, **kwargs):
        """ needed to get STYLE_CHOICES* from the class which uses this Mixin
        """
        super().__init_subclass__(**kwargs)
        style_form_fields = get_style_form_fields(getattr(cls, 'STYLE_CHOICES', None),
            getattr(cls, 'STYLE_CHOICES_MULTIPLE', False))[1:]
        cls.declared_fields.update(zip(['extra_style', 'extra_css'], style_form_fields))
        cls._meta.entangled_fields['config'].extend(['extra_style', 'extra_css'])


class PlusPluginFormBase(DeserializeMixin, forms.ModelForm):
    """
    BaseForm for all none Entangled PluginForms.
    This ModelForm references to a PlusItem Model in order to write and read
    from the glossary (JSONField) attribute.
    """
    attributes = AttributesFormField()

    class Meta:
        model = PlusItem
        exclude = ["_json"]  # Do not show json Field in Edit Form

    def __init__(self, *args, **kwargs):

        if kwargs.get('instance'):
            # set form initial values as our instance model attributes are in
            # glossary not in the instance itself
            initial = kwargs.get('initial', {})

            for field_name, field in self.declared_fields.items():
                initial[field_name] = kwargs.get('instance').glossary.get(field_name)

            kwargs['initial'] = initial
        super(PlusPluginFormBase, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        """
        Put serialized data to glossary (_json) field, then save.
        """
        self.instance.data = self.serialize_data()
        return super(PlusPluginFormBase, self).save(commit)

    def serialize_data(self):
        """
        Takes form field values and calls "serialize_field" method for each field,
        if it is declared in the field class
        :return: Serialized data
        :rtype: dict
        """
        parsed_data = OrderedDict()
        for key in self.fields.keys():
            value = self.cleaned_data.get(key)
            if key.startswith('_'):
                continue

            field = self.fields.get(key)
            if hasattr(field, "serialize_field") and callable(field.serialize_field):
                parsed_data[key] = field.serialize_field(value)
            else:
                parsed_data[key] = value
        return parsed_data
