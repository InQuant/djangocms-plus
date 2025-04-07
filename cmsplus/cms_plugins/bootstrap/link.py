from django import forms
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.forms import PlusStylePluginFormBase, LinkFormMixin
from cmsplus.plugin_base import LinkPluginMixin
from cmsplus.utils import first_choice, insert_fieldset
from cmsplus.cms_plugins.bootstrap.icon import IconField, IconPluginMixin
from cmsplus.cms_plugins.bootstrap.fields import ColorPickerWidget
from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase

# Link
# ----
#
class LinkForm(LinkFormMixin, BootstrapFormBase):
    link_is_optional = False
    STYLE_CHOICES = 'LINK_BUTTON_STYLES'

    name = forms.CharField(
        label=_("Display Name"),
        required=False,
    )

    link_stretched = forms.BooleanField(
        label=_("Stretch link"),
        required=False,
        initial=False,
        help_text=_("Stretches the active link area to the containing block (with position: relative)."),
    )

    LINK_CHOICES = (
        ("link", _("Link")),
        ("btn", _("Button")),
    )
    link_type = forms.ChoiceField(
        label=_("Type"),
        choices=LINK_CHOICES,
        initial=first_choice(LINK_CHOICES),
        widget=forms.RadioSelect(attrs={"class": "inline-block"}),
        help_text=_("Adds either a text link or a button which links to the target."),
    )

    link_color = forms.ChoiceField(
        label=_("Color"),
        choices=cps.EMPTY_CHOICE + cps.COLOR_CHOICES,
        initial=cps.EMPTY_CHOICE[0][0],
        required=False,
        widget=ColorPickerWidget()
    )

    LINK_SIZE_CHOICES = (
        ("btn-sm", _("Small")),
        ("", _("Medium")),
        ("btn-lg", _("Large")),
    )
    link_size = forms.ChoiceField(
        label=_("Button size"),
        choices=LINK_SIZE_CHOICES,
        initial=LINK_SIZE_CHOICES[1][0],  # Medium
        required=False,
    )

    link_outline = forms.BooleanField(
        label=_("Outline"),
        initial=False,
        required=False,
        help_text=_("Removes the coloring from a button and keeps the outline."),
    )

    link_block = forms.BooleanField(
        label=_("Block"),
        initial=False,
        required=False,
        help_text=_("Extends the button to the width of its container."),
    )

    icon_left = IconField(
        label=_("Icon left"),
        initial="",
        required=False,
    )
    icon_right = IconField(
        label=_("Icon right"),
        initial="",
        required=False,
    )


class LinkPlugin(LinkPluginMixin, IconPluginMixin, BootstrapPluginBase):
    footnote_html = "renders a link or button with color."
    form = LinkForm
    name = _("Link / Button")
    text_enabled = True
    allow_children = True
    render_template = 'cmsplus/bootstrap/link-button.html'
    tag_type = 'a'

    text_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-link-45deg" '
        'viewBox="0 0 16 16"><path d="M4.715 6.542 3.343 7.914a3 3 0 1 0 4.243 4.243l1.828-1.829A3 3 0 0 0 8.586 '
        "5.5L8 6.086a1 1 0 0 0-.154.199 2 2 0 0 1 .861 3.337L6.88 11.45a2 2 0 1 1-2.83-2.83l.793-.792a4 4 0 0 "
        '1-.128-1.287z"/><path d="M6.586 4.672A3 3 0 0 0 7.414 9.5l.775-.776a2 2 0 0 1-.896-3.346L9.12 3.55a2 2 0 '
        '1 1 2.83 2.83l-.793.792c.112.42.155.855.128 1.287l1.372-1.372a3 3 0 1 0-4.243-4.243z"/></svg>'
    )

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.name) or str(instance.link)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        name = None

        link_fieldset = (name, {
            'fields': (
                'link',
                'name',
                'target',
                'link_type',
                ('link_color', 'link_size'),
                ('link_stretched', 'link_outline', 'link_block'),
                ('icon_left', 'icon_right',),
            ),
        })
        return insert_fieldset(fieldsets, link_fieldset, 0, self.form.base_fields.keys())

    def render(self, context, instance, placeholder):
        link_classes = []
        if instance.parent and instance.parent.plugin_type == "ListGroupPlugin":
            link_classes.append("list-group-item")
            link_classes.append("list-group-item-action")
            background_prefix = "list-group-item"
        elif (
            getattr(instance, "link_type", "link") == "link"
            and instance.parent
            and instance.parent.plugin_type == "CardInnerPlugin"
        ):
            link_classes.append("card-link")
        else:
            background_prefix = "btn"
        if instance.config.get("link_color", None):
            if getattr(instance, "link_type", "link") == "link":
                link_classes.append(f"link-{instance.link_color}")
            else:
                link_classes.append("btn")
                if not instance.config.get("link_outline"):
                    link_classes.append(f"{background_prefix}-{instance.link_color}")
                else:
                    link_classes.append(f"btn-outline-{instance.link_color}")
        if instance.config.get("link_size", False):
            link_classes.append(instance.link_size)
        if instance.config.get("link_block", False):
            link_classes.append("d-block")
        if instance.config.get("link_stretched", False):
            link_classes.append("stretched-link")
        instance.add_classes(link_classes)
        return super().render(context, instance, placeholder)
