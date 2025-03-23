import logging

from collections import OrderedDict
from django import forms
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from djangocms_frontend import settings as fe_settings
from djangocms_frontend.fields import AttributesFormField
from djangocms_frontend.helpers import get_related_object
from djangocms_frontend.contrib.link.forms import SmartLinkField, MINIMUM_INPUT_LENGTH
from djangocms_frontend.contrib.link import constants as link_const
from djangocms_frontend.contrib.link.helpers import get_choices
from djangocms_frontend.common.title import TitleField
from entangled.forms import EntangledModelForm, EntangledModelFormMixin

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.models import PlusItem
from cmsplus.fields import PlusFilerFileSearchField


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
        self.instance.config = self.serialize_data()
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


# Abstract Link Form
# ------------------
#
class AbstractLinkForm(PlusPluginFormBase):

    link_is_optional = True

    external_link = forms.URLField(
        label=_("External link"),
        required=False,
        #        validators=url_validators,
        help_text=_("Provide a link to an external source."),
    )
    internal_link = SmartLinkField(
        label=_("Internal link"),
        required=False,
        help_text=_("If provided, overrides the external link."),
    )
    file_link = PlusFilerFileSearchField(
        label=_('Download file'),
        required=False,
        help_text=_("An internal link onto a file from filer"),
    )
    # other link types
    anchor = forms.CharField(
        label=_("Anchor"),
        required=False,
        help_text=_(
            "Appends the value only after the internal or external link. "
            'Do <em>not</em> include a preceding "&#35;" symbol.'
        ),
    )
    mailto = forms.EmailField(
        label=_("Email address"),
        required=False,
    )
    phone = forms.CharField(
        label=_("Phone"),
        required=False,
    )
    # advanced options
    target = forms.ChoiceField(
        label=_("Target"),
        choices=fe_settings.EMPTY_CHOICE + link_const.TARGET_CHOICES,
        required=False,
    )
    link_attributes = AttributesFormField(
        label=_("Link attributes"),
        help_text=_("Attributes apply to the <b>link</b>."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["internal_link"].choices = self.get_choices

    def get_choices(self):
        if MINIMUM_INPUT_LENGTH == 0:
            return get_choices(self.request)
        if not self.is_bound:  # find initial value
            int_link_field = self.fields["internal_link"]
            initial = self.get_initial_for_field(int_link_field, "internal_link")
            if initial:  # Initial set?
                obj = get_related_object(dict(obj=initial), "obj")  # get it!
                if obj is not None:
                    value = int_link_field.prepare_value(initial)
                    return ((value, str(obj)),)
        return ()  # nothing found

    def clean(self):
        super().clean()
        link_field_names = (
            "external_link",
            "internal_link",
            "mailto",
            "phone",
            "file_link",
        )
        anchor_field_name = "anchor"
        field_names_allowed_with_anchor = (
            "external_link",
            "internal_link",
        )
        anchor_field_verbose_name = force_str(self.fields[anchor_field_name].label)
        anchor_field_value = self.cleaned_data.get(anchor_field_name, None)
        link_fields = {key: self.cleaned_data.get(key, None) for key in link_field_names}
        link_field_verbose_names = {key: force_str(self.fields[key].label) for key in link_fields.keys()}
        provided_link_fields = {key: value for key, value in link_fields.items() if value}

        if len(provided_link_fields) > 1:
            # Too many fields have a value.
            verbose_names = sorted(link_field_verbose_names.values())
            error_msg = _("Only one of {0} or {1} may be given.").format(
                ", ".join(verbose_names[:-1]),
                verbose_names[-1],
            )
            errors = {}.fromkeys(provided_link_fields.keys(), error_msg)
            raise ValidationError(errors)

        if (
            len(provided_link_fields) == 0
            and not self.cleaned_data.get(anchor_field_name, None)
            and not self.link_is_optional
        ):
            raise ValidationError(_("Please provide a link."))

        if anchor_field_value:
            for field_name in provided_link_fields.keys():
                if field_name not in field_names_allowed_with_anchor:
                    error_msg = _("%(anchor_field_verbose_name)s is not allowed together with %(field_name)s") % {
                        "anchor_field_verbose_name": anchor_field_verbose_name,
                        "field_name": link_field_verbose_names.get(field_name),
                    }
                    raise ValidationError(
                        {
                            anchor_field_name: error_msg,
                            field_name: error_msg,
                        }
                    )
