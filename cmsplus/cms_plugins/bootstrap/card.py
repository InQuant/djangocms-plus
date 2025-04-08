from re import I
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.cms_plugins.bootstrap.base import BootstrapPluginBase, BootstrapFormBase
from cmsplus.cms_plugins.bootstrap.fields import RowColsWidget, ColorPickerWidget
from cmsplus.cms_plugins.bootstrap.grid import SPACING_FIELD, BACKGROUND_COLOR_FIELD, FLEX_FIELD, TEXT_COLOR_FIELD
from cmsplus.utils import first_choice, link_to_bootstrap_doc, insert_fieldset

NO_BORDER_FIELD = forms.BooleanField(
        label=_("No Border"),
        initial=False,
        required=False,
        help_text=_("If checked item will have no border."),
    )

# CardLayout
# ----------
#
class CardLayoutForm(BootstrapFormBase):
    """
    Components > "Card" Plugin
    https://getbootstrap.com/docs/5.3/components/card/
    """

    CARD_LAYOUT_TYPE_CHOICES = (
        ("card-group", "Card group"),
        ("row", "Grid cards"),
    )
    card_type = forms.ChoiceField(
        label=_("Card type"),
        choices=CARD_LAYOUT_TYPE_CHOICES,
        initial=first_choice(CARD_LAYOUT_TYPE_CHOICES),
        help_text=link_to_bootstrap_doc('components/card/#card-layout')
    )

    row_columns = forms.CharField(label="Row Columns", required=False, widget=RowColsWidget)

class CardLayoutPlugin(BootstrapPluginBase):
    """
    Components > "Card" Plugin
    https://getbootstrap.com/docs/5.0/components/card/
    """
    footnote_html = """
    Renders a bootstrap Card Layout component.
    """
    name = _("Card layout")
    form = CardLayoutForm
    allow_children = True
    child_classes = [ "CardPlugin", ]

    def render(self, context, instance, placeholder):
        instance.add_classes(instance.card_type)
        if instance.row_columns:
            instance.add_classes(instance.row_columns)
        return super().render(context, instance, placeholder)

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.card_type)

# Card
# ----
#
class CardForm(BootstrapFormBase):
    """
    Components > "Card" Plugin
    https://getbootstrap.com/docs/5.0/components/card/
    """

    CARD_COLOR_STYLE_CHOICES = cps.COLOR_CHOICES + (("transparent", _("Transparent")),)
    card_outline = forms.ChoiceField(
        label=_("Card Outline"),
        initial=cps.EMPTY_CHOICE[0][0],
        choices=cps.EMPTY_CHOICE + CARD_COLOR_STYLE_CHOICES,
        required=False,
        help_text=_("Uses the border to indicate context."),
        widget=ColorPickerWidget
    )

    CARD_ALIGNMENT_CHOICES = (
        ("start", _("Left")),
        ("center", _("Center")),
        ("end", _("Right")),
    )
    card_alignment = forms.ChoiceField(
        label=_("Alignment"),
        choices=cps.EMPTY_CHOICE + CARD_ALIGNMENT_CHOICES,
        required=False
    )

    card_full_height = forms.BooleanField(
        label=_("Full height"),
        initial=False,
        required=False,
        help_text=_("If checked cards in one row will automatically extend to the full row height."),
    )

    no_border = NO_BORDER_FIELD
    card_text_color = TEXT_COLOR_FIELD
    spacing = SPACING_FIELD

class CardPlugin(BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap Card component.
    """
    name = "Card"
    form = CardForm
    allow_children = True
    child_classes = [
        "CardInnerPlugin",
        "ListGroupPlugin",
        "ImagePlugin",
        "GridRowPlugin",
        "GridContainerPlugin",
    ]
    render_template = 'cmsplus/bootstrap/card.html'

    card_fieldset = (
        None,
        {
            "fields": (
                (
                    "card_outline",
                    "card_text_color",
                    "card_alignment",
                ),
                ('no_border', 'card_full_height',),
                ('spacing',),
            )
        },
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        keys_to_remove = self.form.declared_fields.keys()
        return insert_fieldset(fieldsets, self.card_fieldset, 0, keys_to_remove)

    def render(self, context, instance, placeholder):
        instance.add_classes("card", "position-relative")
        if instance.config.get("card_outline", None):
            instance.add_classes(f"border-{instance.card_outline}")
        if instance.card_alignment:
            instance.add_classes(f"text-{instance.card_alignment}")
        if instance.config.get("card_text_color", None):
            instance.add_classes(f"text-{instance.card_text_color}")
        if instance.config.get("card_full_height", None):
            instance.add_classes("h-100")
        if instance.spacing:
            instance.add_classes(instance.spacing)
        if instance.parent and instance.parent.plugin_type == "CardLayoutPlugin":
            if instance.parent.get_plugin_instance()[0].card_type == "row":
                instance.add_classes("h-100")
        if instance.no_border:
            instance.add_classes("border-0")
        return super().render(context, instance, placeholder)

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.card_text_color) or str(instance.card_outline) or " "


# CardInner (header, body, footer)
# --------------------------------
#
class CardInnerForm(BootstrapFormBase):
    CARD_INNER_TYPE_CHOICES = (
        ("card-body", "Body"),
        ("card-header", "Header"),
        ("card-footer", "Footer"),
        ("card-img-overlay", "Image overlay"),
    )
    inner_type = forms.ChoiceField(
        label=_("Inner type"),
        choices=CARD_INNER_TYPE_CHOICES,
        initial=first_choice(CARD_INNER_TYPE_CHOICES),
        help_text=_("Define the structure of the plugin."),
    )

    ALIGN_CHOICES = (
        ("start", _("Left")),
        ("center", _("Center")),
        ("end", _("Right")),
    )
    text_alignment = forms.ChoiceField(
        label=_("Content alignment"),
        choices=cps.EMPTY_CHOICE + ALIGN_CHOICES,
        required=False,
    )

    overlay_img_filter = forms.ChoiceField(
        label=_("Image Filter"),
        choices=cps.EMPTY_CHOICE + cps.IMG_FILTER_CHOICES,
        required=False,
    )

    no_border = NO_BORDER_FIELD
    flex = FLEX_FIELD
    spacing = SPACING_FIELD
    text_color = TEXT_COLOR_FIELD
    background_color = BACKGROUND_COLOR_FIELD

    def clean(self):
        super().clean()
        if self.cleaned_data.get('overlay_img_filter') and not self.cleaned_data.get('inner_type') == 'card-img-overlay':
            raise ValidationError(
                force_str(_("Inner type of 'Image Overlay' is required if 'Image Filter' is selected.")),
                code="required",
            )


class CardInnerPlugin(BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap Card structure component (header, body, footer).
    """
    name = _("Card Item")
    form = CardInnerForm
    allow_children = True
    parent_classes = [
        "CardPlugin",
        "GridColumnPlugin",
        "GridContainerPlugin",
    ]
    render_template = 'cmsplus/bootstrap/card-inner.html' # due to overlay_img_filter

    inner_fieldset = (
        None,
        {
            "fields": (
                (
                    "inner_type",
                    "text_alignment",
                    "overlay_img_filter",
                    "no_border",
                ),
                ('flex',),
                ('spacing',),
                ('text_color', ('background_color'),),
            )
        },
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        keys_to_remove = self.form.declared_fields.keys()
        return insert_fieldset(fieldsets, self.inner_fieldset, 0, keys_to_remove)

    def render(self, context, instance, placeholder):
        for k in ['inner_type', 'text_alignment', 'flex', 'spacing', 'no_border', 'text_color', 'background_color']:
            if getattr(instance, k, None):
                v = getattr(instance, k)
                if k in ['text_alignment', 'text_color']: v = 'text-' + v
                if k == 'background_color': v = 'bg-' + v
                if k == 'no_border': v = 'border-0'
                instance.add_classes(v)

        return super().render(context, instance, placeholder)

    @classmethod
    def get_identifier(cls, instance):
        tmap = dict(cls.form.CARD_INNER_TYPE_CHOICES)
        return str(tmap.get(instance.inner_type))
