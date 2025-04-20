import json
import logging
import re
from abc import abstractmethod, ABC
from datetime import datetime
from webbrowser import get
from cms.models import Page
from cms.utils import get_current_site
from django import forms
from django.contrib.admin.sites import site as admin_site
from django.contrib.admin.widgets import AdminSplitDateTime
from django.core.exceptions import ValidationError, ObjectDoesNotExist, MultipleObjectsReturned
from django.core.validators import ProhibitNullCharactersValidator, RegexValidator
from django.db.models.fields.related import ManyToOneRel
from django.forms.fields import Field
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _, gettext
from django.utils.safestring import mark_safe
from filer.fields.file import AdminFileWidget, FilerFileField
from filer.fields.image import FilerImageField
from filer.models.filemodels import File as FilerFileModel
from filer.models.imagemodels import Image as FilerImageModel
from djangocms_attributes_field import fields
from djangocms_link.fields import LinkWidget as LinkWidgetBase, LinkFormField

from cmsplus.widgets import KeyValueWidget

logger = logging.getLogger(__name__)


class BaseFieldMixIn(ABC):
    @abstractmethod
    def serialize_field(self, value):
        pass

    @abstractmethod
    def deserialize_field(self, value):
        pass

class AttributesFormField(fields.AttributesFormField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", _("Attributes"))
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", fields.AttributesWidget)
        self.excluded_keys = kwargs.pop("excluded_keys", [])
        super().__init__(*args, **kwargs)


class TitleWidget(forms.MultiWidget):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widgets",
            (
                forms.CheckboxInput(),
                forms.TextInput(),
            ),
        )
        super().__init__(*args, **kwargs)

    def decompress(self, value):
        if isinstance(value, dict):
            return [value.get("show", False), value.get("title", "")]
        return [False, ""]

    def render(self, name, value, attrs=None, renderer=None):
        value = self.decompress(value)
        rendered_widgets = [
            widget.render(f"{name}_{i}", val, attrs=attrs, renderer=renderer)
            for i, (widget, val) in enumerate(zip(self.widgets, value))
        ]
        # Wrap both in a div with inline style or class for styling
        return mark_safe(f'''
            <div style="display: flex; gap: 10px; align-items: center;">
                <label style="white-space: nowrap;">Show: {rendered_widgets[0]}</label>
                <label style="flex-grow: 1;">Title: {rendered_widgets[1]}</label>
            </div>
        ''')


class TitleField(forms.MultiValueField):
    def __init__(self, **kwargs):
        fields = (
            forms.BooleanField(required=False),
            forms.CharField(required=False),
        )
        super().__init__(fields=fields, require_all_fields=False, widget=TitleWidget, **kwargs)


    def clean(self, value):
        if value[0] and not value[1]:
            raise ValidationError(_("Please add a title if you want to publish it."), code="incomplete")
        return super().clean(value)

    def compress(self, data_list):
        if data_list is None:
            return {'show': False, 'title': ''}
        return dict(show=data_list[0], title=data_list[1])


class PlusModelMultipleChoiceField(forms.ModelMultipleChoiceField, BaseFieldMixIn):
    def serialize_field(self, qs):
        return {
            'model': '{}.{}'.format(qs.model._meta.app_label, qs.model._meta.model_name),
            'p_keys': list(qs.values_list("pk", flat=True)),
            'names': [str(obj) for obj in qs]
        }

    def deserialize_field(self, value: list):
        if value is None:
            return None
        return self.queryset.filter(pk__in=value["p_keys"])


class PlusModelChoiceField(forms.ModelChoiceField, BaseFieldMixIn):
    def serialize_field(self, obj: object):
        if not obj: return None
        return {
            'model': '{}.{}'.format(obj._meta.app_label, obj._meta.model_name),
            'pk': getattr(obj, 'pk', None),
            'name': str(obj), # no function - for humans only
        }

    def deserialize_field(self, value):
        if value is None:
            return None
        try:
            return self.queryset.get(pk=value["pk"])
        except ObjectDoesNotExist as e:
            raise ValidationError('PlusModelChoiceField Deserialization Error: Could not find %s object with pk %s' %
                                  (self.queryset.model.__name__, value))

    def to_python(self, value):
        key = self.to_field_name or 'pk'

        # fix for invalid choice error; sometimes value is an object instead pk
        # TypeError: int() argument must be a string, a bytes-like object or a number, not 'Page')
        value_pk = getattr(value, key, None)
        if not value_pk:
            value_pk = value

        if value in self.empty_values:
            return None

        try:
            key = self.to_field_name or 'pk'
            value = self.queryset.get(**{key: value_pk})
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
        return value


class PageChoiceIterator(forms.models.ModelChoiceIterator):
    """ Sort pages by absolute url. """

    def __iter__(self):
        if self.field.empty_label is not None:
            yield "", self.field.empty_label

        pages = sorted(self.queryset.all(), key=lambda p: p.get_absolute_url())
        for obj in pages:
            yield self.choice(obj)


class PageSearchField(PlusModelChoiceField):
    iterator = PageChoiceIterator

    def __init__(self, *args, **kwargs):
        queryset = Page.objects.all()
        try:
            queryset = queryset.on_site(get_current_site())
        except Exception:
            pass  # can happen if database is not ready yet
        kwargs.setdefault('queryset', queryset)
        super().__init__(*args, **kwargs)

    def serialize_field(self, obj: object):
        if not obj: return None
        ser_val = super().serialize_field(obj)
        try:
            ser_val['absolute_url'] = obj.get_absolute_url()
        except Exception:
            pass
        return ser_val

    def label_from_instance(self, obj):
        """
        Display value is the absolute url, sorted via iterator above.
        """
        return obj.get_absolute_url()

class FilerSerializeMixin:

    def serialize_field(self, obj: object):
        if not obj: return None
        ser_val = super().serialize_field(obj)
        try:
            ser_val['sha1'] = obj.sha1
        except:
            pass
        return ser_val

    def deserialize_field(self, value):
        if value is None:
            return None
        try:
            return super().deserialize_field(value)
        except:
            pass # next try via sha1

        try:
            return self.queryset.get(sha1=value["sha1"])
        except MultipleObjectsReturned:
            return self.queryset.filter(sha1=value["sha1"]).first()
        except (KeyError, ObjectDoesNotExist) as e:
            raise ValidationError('Filer Field Deserialization Error: Could not find %s object with pk %s or sha1' %
                                  (self.queryset.model.__name__, value))

class PlusFilerFileSearchField(FilerSerializeMixin, PlusModelChoiceField):

    def __init__(
            self,
            queryset=FilerFileModel.objects.all(),
            widget=AdminFileWidget(
                ManyToOneRel(FilerFileField, FilerFileModel, 'id'), admin_site),
            *args, **kwargs
    ):
        super().__init__(queryset=queryset, widget=widget, *args, **kwargs)


class PlusFilerImageSearchField(FilerSerializeMixin, PlusModelChoiceField):

    def __init__(
            self,
            queryset=FilerImageModel.objects.all(),
            widget=AdminFileWidget(
                ManyToOneRel(FilerImageField, FilerImageModel, 'id'), admin_site),
            *args, **kwargs
    ):
        super().__init__(queryset=queryset, widget=widget, *args, **kwargs)


# SizeField
# ---------
#
NUMBER_REGEX = r'^[-+]?([0-9]+(\.[0-9]+)?|\.[0-9]+)'
UNSIGNED_NUMBER_REGEX = r'^([0-9]+(\.[0-9]+)?|\.[0-9]+)'
NUMBER_PAT = re.compile(NUMBER_REGEX)


@deconstructible
class SizeUnitValidator:
    """
    Taken and adopted from cmsplugin_cascade.fields
    """
    allowed_units = []
    message = _("'%(value)s' is not a valid size unit. Allowed units are: %(allowed_units)s.")
    code = 'invalid_size_unit'

    def __init__(self, allowed_units=None, allow_negative=True):
        possible_units = ['vw', 'vh', 'rem', 'px', 'em', '%', 'auto']
        if allowed_units is None:
            self.allowed_units = possible_units
        else:
            self.allowed_units = [au for au in allowed_units if au in possible_units]
        units_with_value = list(self.allowed_units)
        if 'auto' in self.allowed_units:
            self.allow_auto = True
            units_with_value.remove('auto')
        else:
            self.allow_auto = False
        if allow_negative:
            patterns = '{}({})$'.format(NUMBER_REGEX, '|'.join(units_with_value))
        else:
            patterns = '{}({})$'.format(UNSIGNED_NUMBER_REGEX, '|'.join(units_with_value))
        self.validation_pattern = re.compile(patterns)

    def __call__(self, value):
        if self.allow_auto and value == 'auto':
            return
        match = self.validation_pattern.match(value)
        if not (match and match.group(1).isdigit()):
            allowed_units = " {} ".format(gettext("or")).join("'{}'".format(u) for u in self.allowed_units)
            params = {'value': value, 'allowed_units': allowed_units}
            raise ValidationError(self.message, code=self.code, params=params)

    def __eq__(self, other):
        return (
                isinstance(other, self.__class__) and
                self.allowed_units == other.allowed_units and
                self.message == other.message and
                self.code == other.code
        )


class SizeField(Field):
    """
    Use this field for validating input containing a value ending in ``px``, ``em``, ``rem`` or ``%``.
    Use it for values representing a size, margin, padding, width or height.
    """

    def __init__(self, *, allowed_units=None, **kwargs):
        self.empty_value = ''
        super().__init__(**kwargs)
        self.validators.append(SizeUnitValidator(allowed_units))
        self.validators.append(ProhibitNullCharactersValidator())

    def to_python(self, value):
        """Return a stripped string."""
        if value not in self.empty_values:
            value = str(value).strip()
        if value in self.empty_values:
            return self.empty_value
        return value

    @staticmethod
    def get_number_part(value):
        m = NUMBER_PAT.search(value)
        try:
            return int(m.group())
        except ValueError:
            return float(m.group())


regex_key_validator = RegexValidator(regex=r'^[a-z][-a-z0-9_]*\Z',
                                     flags=re.IGNORECASE, code='invalid')


class KeyValueField(forms.CharField):
    empty_values = [None, '']

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', KeyValueWidget)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except ValueError as exc:
                raise forms.ValidationError(
                    f'JSON decode error: {exc}'
                )
        else:
            return value


class PlusSplitDateTimeField(forms.SplitDateTimeField, BaseFieldMixIn):
    widget = AdminSplitDateTime

    def deserialize_field(self, value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        except TypeError:
            pass

    def serialize_field(self, value: datetime):
        if not value or value == "":
            return
        return value.isoformat()


class PlusDateTimeField(forms.DateTimeField, BaseFieldMixIn):
    widget = AdminSplitDateTime

    def deserialize_field(self, value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
        except TypeError:
            pass

    def serialize_field(self, value: datetime):
        if not value or value == "":
            return
        return value.isoformat()

# LinkWidget
# ----------
class LinkWidget(LinkWidgetBase):
    """ Form(data=data).is_valid() does not work with the ori LinkWidget

    to push the correct data into the form bound filed - value_from_datadict has to be overwritten.
    """

    def value_from_datadict(self, data, files, name):
        """
        Possible data dicts:

        1. if via post from form: query dict: <QueryDict: {
            ...
            'link_0': ['external_link'],
            'link_1': ['https://www.inquant.de'],
            'link_2': [''],
            'link_3': [''],
            'link_4': [''],
            ...
            '_save': ['Speichern']
        }>

        2. If given via __init__(data):
        {
            ...
            link: {'external_link', 'https://www.inquant.de'}
            # or:
            link: {'internal_link', 'cms.page:1', 'anchor': '#foo'}
            # or:
            link: {'file_link', '67'}
            ...
        }

        possible widget value combinations:

        ['external_link', 'https://www.inquant.de', '', '', '']
        ['internal_link', '', 'cms.page:1', '#foo', '']
        ['file_link', '', '', '', '67']
        """
        raw_values = super().value_from_datadict(data, files, name)
        if name in data and raw_values == [None, None, None, None, None]:
            logger.warn(f'** LinkWidget.value_from_datadict(): fixing raw_values from: ({raw_values})')
            value = data[name]
            raw_values = value if isinstance(value, list) else self._build_widget_value_list_from_dict(value)
            logger.warn(f'** to: {raw_values}')

        return raw_values

    def _build_widget_value_list_from_dict(self, dict_value: dict) -> list[str | None]:
        """
        transforms input combinations of:
            link: {'external_link', 'https://www.inquant.de'}
            # or:
            link: {'internal_link', 'cms.page:1', 'anchor': '#foo'}
            # or:
            link: {'file_link', '67'}

        into output combinations:

            ['external_link', 'https://www.inquant.de', '', '', '']
            # or:
            ['internal_link', '', 'cms.page:1', '#foo', '']
            # or:
            ['file_link', '', '', '', '67']

        """
        _get_pos = self.data_pos.get

        values = [''] * len(self.widgets)

        if not dict_value or not isinstance(dict_value, dict):
            return values

        link_type = next((key for key in dict_value if key != "anchor"), None)
        anchor = dict_value.get("anchor", "")

        if not link_type:
            return values

        values[0] = link_type

        # Pos of subwidgets
        link_pos = _get_pos(link_type)
        anchor_pos = _get_pos('anchor')

        if link_pos is not None:
            values[link_pos] = dict_value[link_type]

        if link_type == "internal_link" and anchor_pos is not None:
            values[anchor_pos] = anchor

        return values


class LinkField(LinkFormField):
    widget = LinkWidget
