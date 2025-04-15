from django import forms
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.forms import LinkFormMixin
from cmsplus.plugin_base import LinkPluginMixin
from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase
from cmsplus.cms_plugins.bootstrap.fields import BACKGROUND_COLOR_FIELD, SPACING_FIELD

# List Group
# ----------
class ListGroupForm(BootstrapFormBase):
    list_group_numbered = forms.BooleanField(
        label=_("List group numbered"),
        initial=False,
        required=False,
        help_text="list items are numbered.",
    )

    list_group_flush = forms.BooleanField(
        label=_("List group flush"),
        initial=False,
        required=False,
        help_text="Create lists of content (e.g. in a card) with flushed (some borders removed) list items.",
    )

    list_group_horizontal = forms.CharField(
        label=_("Horizontal list items"),
        required=False,
        initial="",
        help_text="Define horizontal classes, e.g.: list-group-horizontal-lg",
    )

    spacing = SPACING_FIELD

class ListGroupPlugin(BootstrapPluginBase):
    footnote_html = f"""
Renders a bootstrap List Group.

Components > "List Group" Plugin
See: <a href="{cps.BOOTSTRAP_DOC_URL}/components/list-group/">List Group Documentation</a>
    """
    name = "List group"
    form = ListGroupForm
    allow_children = True
    child_classes = ["ListGroupItemPlugin", "TextLinkPlugin"]
    render_template = 'cmsplus/bootstrap/list-group.html' # due to GridRowPlugin as parent
    tag_type = 'ul'

    def render(self, context, instance, placeholder):
        instance.add_classes("list-group")
        for k in ['list_group_numbered', 'list_group_flush', 'list_group_horizontal', 'spacing']:
            if getattr(instance, k, None):
                v = getattr(instance, k)
                if k == 'list_group_numbered': v = 'list-group-numbered'
                elif k == 'list_group_flush': v = 'list-group-flush'
                instance.add_classes(v)
        return super().render(context, instance, placeholder)


# List Group Item
# ---------------
class ListGroupItemForm(LinkFormMixin, BootstrapFormBase):
    require_link = False

    simple_content = forms.CharField(
        label=_("One line content"),
        required=False,
        help_text=_("List item text. Is only show if this list item has no child plugins."),
    )

    background_color = BACKGROUND_COLOR_FIELD


class ListGroupItemPlugin(LinkPluginMixin, BootstrapPluginBase):
    f"""
Renders a Components > "List Group Item" Plugin

See: <a href="{cps.BOOTSTRAP_DOC_URL}/components/list-group/">List Group Documentation</a>
    """
    name = "List Item"
    form = ListGroupItemForm
    allow_children = True
    parent_classes = ["ListGroupPlugin"]
    render_template = 'cmsplus/bootstrap/list-group-item.html' # due to link
    tag_type = 'li'

    def render(self, context, instance, placeholder):
        instance.add_classes("list-group-item")
        if instance.background_color:
            instance.add_classes(f"list-group-item-{instance.background_color}")
        if instance.link:
            instance.add_classes('list-group-item-action')

        return super().render(context, instance, placeholder)
