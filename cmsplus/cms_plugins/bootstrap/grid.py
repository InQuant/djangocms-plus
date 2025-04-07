import logging
import urllib.parse

from django import forms
from django.forms import widgets
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.forms import PlusPluginFormBase, PlusStylePluginFormBase
from cmsplus.models import PlusItem
from cmsplus.plugin_base import PlusPlugin, PlusStylePlugin
from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase
from cmsplus.cms_plugins.bootstrap.fields import ColorPickerWidget, SpacingWidget, FlexWidget, RowColsWidget, ColsWidget
from cmsplus.cms_plugins.bootstrap.mixins import BackgroundImagePluginMixin, BackgroundImageFormMixin
from cmsplus.utils import insert_fieldset

logger = logging.getLogger(__name__)

# Spacer
# ------
#

FLEX_FIELD = forms.CharField(label="Flex Grid", required=False, widget=FlexWidget)
SPACING_FIELD = forms.CharField(label="Spacing", required=False, widget=SpacingWidget)
BACKGROUND_COLOR_FIELD = forms.ChoiceField(
        choices=cps.EMPTY_CHOICE + cps.COLOR_CHOICES,
        label=_("Background Color"),
        required=False,
        initial="",
        help_text=_('Select a background color.'),
        widget=ColorPickerWidget()
    )
TEXT_COLOR_FIELD = forms.ChoiceField(
        choices=cps.EMPTY_CHOICE + cps.COLOR_CHOICES,
        label=_("Text Color"),
        required=False,
        initial="",
        help_text=_('Select a text color.'),
        widget=ColorPickerWidget()
    )

class SpacerForm(BootstrapFormBase):
    STYLE_CHOICES = 'SPACER_STYLES'

    spacing = forms.CharField(label="Spacing", required=True, widget=SpacingWidget)


class SpacerPlugin(BootstrapPluginBase):
    footnote_html = """
    Renders a spacer realize a space between plugins.
    """
    name = 'Spacer'
    form = SpacerForm
    allow_children = False
    parent_classes = None
    require_parent = False

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.spacing)

    def render(self, context, instance, placeholder):
        if getattr(instance, 'spacing', None):
            instance.add_classes(getattr(instance, 'spacing'))
        return super().render(context, instance, placeholder)


# GridContainer
# -------------
#
class GridContainerForm(BackgroundImageFormMixin, BootstrapFormBase):
    STYLE_CHOICES = 'MOD_CONTAINER_STYLES'

    FLUID_CHOICES = (
        ('', 'Full no margin'),
        ('container', _('Fixed Content')),
        ('container-fluid', _('Fluid Content')),
    )
    fluid = forms.ChoiceField(
        label=_('Container Type'),
        initial='',
        required=False,
        choices=FLUID_CHOICES,
        help_text=_('Changing your container from "Fluid no margin" to "fixed content with fluid '
                    'margin" or to "fluid content with fixed margin".')
    )

    flex = FLEX_FIELD
    spacing = SPACING_FIELD
    background_color = BACKGROUND_COLOR_FIELD
    text_color = TEXT_COLOR_FIELD


class GridContainerPlugin(BackgroundImagePluginMixin, BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap container fix or fluid for device classes of:</p>
     <ul>
     <li>XS: Portrait Phones (<576px)</li>
     <li>SM: Small Tablets  (≥576px and <768px)</li>
     <li>MD: Tablets (≥768px and <992px)</li>
     <li>LG: Laptops (≥992px and <1.200px)</li>
     <li>XL: Desktops (≥1.200px and <1.600px)</li>
     <li>XXL: Large Desktops (≥1.600px and < 1.900px)</li>
     <ul>
    """
    name = 'Container'
    form = GridContainerForm
    allow_children = True
    parent_classes = None
    require_parent = False

    cnt_fieldset = (
        None,
        {
            "fields": (
                ("fluid",),
                ("flex",),
                ("spacing",),
                ("background_color", "text_color"),
            )
        },
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        keys_to_remove = self.form.declared_fields.keys()
        return insert_fieldset(fieldsets, self.cnt_fieldset, 0, keys_to_remove)

    def render(self, context, instance, placeholder):
        for k in ['fluid', 'flex', 'spacing', 'background_color', 'text_color']:
            if getattr(instance, k, None):
                v = getattr(instance, k)
                if k == 'background_color': v = 'bg-' + v
                if k == 'text_color': v = 'text-' + v
                instance.add_classes(v)
        return super().render(context, instance, placeholder)

    @classmethod
    def get_identifier(cls, instance):
        cnt_map = dict(cls.form.FLUID_CHOICES)
        ident = cnt_map.get(instance.glossary.get('fluid'))
        style_map = dict(getattr(cps, cls.form.STYLE_CHOICES, {}))
        style = style_map.get(instance.glossary.get('extra_style'))
        return style if style != 'None' else ident

# GridRow
# -------
#
class GridRowForm(BootstrapFormBase):
    STYLE_CHOICES = 'MOD_ROW_STYLES'

    row_columns = forms.CharField(label="Row Columns", required=False, widget=RowColsWidget)
    spacing = SPACING_FIELD

class GridRowPlugin(BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap (grid) row.
    """
    name = 'Row'
    form = GridRowForm

    child_classes = ["GridColumnPlugin", "CardPlugin"]
    allow_children = True

    def render(self, context, instance, placeholder):
        instance.add_classes('row')
        for k in ['row_columns', 'spacing']:
            if getattr(instance, k, None):
                v = getattr(instance, k)
                instance.add_classes(v)
        return super().render(context, instance, placeholder)

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.row_columns) or str(instance.spacing)


# GridColumn
# ----------
#
class GridColumnForm(BackgroundImageFormMixin, BootstrapFormBase):

    STYLE_CHOICES = 'MOD_COL_STYLES'

    columns = forms.CharField(label="Columns", required=False, widget=ColsWidget)
    flex = FLEX_FIELD
    spacing = SPACING_FIELD
    background_color = BACKGROUND_COLOR_FIELD
    text_color = TEXT_COLOR_FIELD


class GridColumnPlugin(BackgroundImagePluginMixin, BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap column with various column classes and spacing.
    """
    name = 'Column'
    form = GridColumnForm
    parent_classes = ['GridRowPlugin',]
    require_parent = True
    allow_children = True

    cnt_fieldset = (
        None,
        {
            "fields": (
                ("columns",),
                ("flex",),
                ("spacing",),
                ("background_color", "text_color"),
            )
        },
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        keys_to_remove = self.form.declared_fields.keys()
        return insert_fieldset(fieldsets, self.cnt_fieldset, 0, keys_to_remove)


    def render(self, context, instance, placeholder):
        instance.add_classes('col')
        for k in ['columns', 'flex', 'spacing', 'background_color', 'text_color']:
            if getattr(instance, k, None):
                v = getattr(instance, k)
                if k == 'background_color': v = 'bg-' + v
                if k == 'text_color': v = 'text-' + v
                instance.add_classes(v)
        return super().render(context, instance, placeholder)

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.columns) or str(instance.spacing) or str(instance.background_color)
