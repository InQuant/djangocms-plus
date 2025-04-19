import logging

from collections import OrderedDict
from django import forms
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from djangocms_link.fields import LinkFormField

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.models import PlusItem
from cmsplus.fields import PlusFilerImageSearchField, AttributesFormField, TitleField
from cmsplus.cms_plugins.bootstrap.fields import DisplayWidget


logger = logging.getLogger(__name__)


class SerializeMixin:

    def deserialize(self):
        """
        Deserialize data from Json field into dict. Opposite of serialize function (see above)
        :return: Data
        :rtype: dict:
        """
        parsed_dict = OrderedDict()

        for field_name in self.declared_fields:
            if self._meta.exclude and field_name in self._meta.exclude: continue
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

    def serialize(self):
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


class PlusPluginFormBase(SerializeMixin, forms.ModelForm):
    """
    BaseForm for all  PluginForms.
    This ModelForm references to a PlusItem Model in order to write and read
    from the glossary (JSONField) attribute.
    """

    plugin_title = TitleField(
        label=_("Title"),
        required=False,
        help_text=_(
            "Optional title of the plugin for easier identification. "
            "Its <code>title</code> attribute "
            "will only be set if the checkbox is selected."
        ),)

    attributes = AttributesFormField(
        label=_('Attributes'), required=False, initial='',
        help_text=_('Add extra html attributes, e.g: class="mx-3 mx-lg-5"'))

    display = forms.CharField(label="Display", required=False, widget=DisplayWidget)

    class Meta:
        model = PlusItem
        exclude = ['_json']

    def __init__(self, *args, glossary=None, **kwargs):
        if kwargs.get('instance'):
            # set form initial values as our instance model attributes are in
            # glossary not in the instance itself
            initial = kwargs.get('initial', {})

            for field_name, field in self.declared_fields.items():
                initial[field_name] = kwargs.get('instance').glossary.get(field_name)

            kwargs.setdefault('initial', initial)

        if glossary:
            # init data from glossary
            data = self.get_form_init_data(glossary)
            kwargs['data'] = data

        super().__init__(*args, **kwargs)

    def get_form_init_data(self, glossary):
        def prepare_value(field, value):
            if hasattr(field, 'prepare_value'):
                return field.prepare_value(value)
            return value

        data = {}
        for k, v in glossary.items():
            if not k in self.declared_fields: continue
            field = self.declared_fields[k]
            data[k] = prepare_value(field, v)
        return data

    def save(self, commit=True):
        """
        Put serialized data to glossary (config) field, then save.
        """
        self.instance.config = self.serialize()
        return super().save(commit)


# Style Form
# ----------
#
class PlusStylePluginFormBase(PlusPluginFormBase):
    style_choices = (
        ('', 'None'),
    )

    extra_style = forms.ChoiceField(
            label=_('Style'), required=False, choices=style_choices,
            initial='', help_text=_('Extra CSS predefined style class for plugin.')
        )
    extra_css = AttributesFormField(
            label=_('Extra CSS'), required=False, initial='',
            help_text=_('Add extra (device specific) css key, values, e.g: margin or margin:md or transform:xl')
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if getattr(self, 'STYLE_CHOICES', None):
            choices = getattr(cps, getattr(self, 'STYLE_CHOICES'), None)
            if choices:
                self.fields['extra_style'].choices = choices
                self.fields['extra_style'].initial = choices[0][0]
        elif getattr(self, 'MULTIPLE_STYLE_CHOICES', None):
            choices = getattr(cps, getattr(self, 'MULTIPLE_STYLE_CHOICES'), None)
            if choices:
                self.fields['extra_style'] = forms.MultipleChoiceField(
                    label=_('Style'), choices=choices, required=False,
                    initial=choices[0][0],
                    help_text=_('Extra predefined style classes for plugin.')
                )


# Link Form Mixin
# ---------------
#
TARGET_CHOICES = (
    ("_blank", _("Open in new window")),
    ("_self", _("Open in same window")),
    ("_parent", _("Delegate to parent")),
    ("_top", _("Delegate to top")),
)
class LinkFormMixin(forms.Form):

    link_is_optional = True

    link = LinkFormField(
        label=_("Link"),
        initial={},
        required=False,
    )

    target = forms.ChoiceField(
        label=_("Target"),
        choices=cps.EMPTY_CHOICE + TARGET_CHOICES,
        required=False,
    )

    link_attributes = AttributesFormField(
        label=_("Link attributes"),
        help_text=_("Attributes apply to the <b>link</b>."),
    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["link"].required = not self.link_is_optional

    def clean(self):
        super(LinkFormMixin, self).clean()
        if not self.link_is_optional and not self.cleaned_data.get('link'):
            raise ValidationError(
                force_str(_("Link is required.")),
                code="required",
            )
