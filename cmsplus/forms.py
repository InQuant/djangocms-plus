import logging

from collections import OrderedDict
from django import forms
from django.core.exceptions import ValidationError
from django.db.models.fields.related import ManyToOneRel
from django.utils.translation import gettext_lazy as _

from djangocms_frontend.contrib.grid.forms import GridContainerForm as GridContainerFormBase
from entangled.forms import EntangledModelForm, EntangledModelFormMixin
from filer.fields.image import AdminImageFormField, FilerImageField
from filer.models import Image

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import KeyValueField
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
        extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)


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
        style_field(
            label=_('Style'), required=False, choices=sc,
            initial=sc[0][0], help_text=_('Extra CSS predefined style class for plugin.')
        ),
        KeyValueField(
            label=_('Extra CSS'), required=False, initial='',
            help_text=_('Add extra (device specific) css key, values, e.g: margin or margin:md or transform:xl'))
    ]


class PlusStyleFormMixin(DeserializeMixin, EntangledModelFormMixin):

    class Meta:
        entangled_fields = {
            "config": []
        }

    def __init_subclass__(cls, **kwargs):
        """ needed to get STYLE_CHOICES* from the class which uses this Mixin
        """
        super().__init_subclass__(**kwargs)
        cls.declared_fields.update(
            zip(['extra_style', 'extra_css'], get_style_form_fields(
                getattr(cls, 'STYLE_CHOICES', None), getattr(cls, 'STYLE_CHOICES_MULTIPLE', False))))
        cls._meta.entangled_fields['config'].extend(['extra_style', 'extra_css'])
