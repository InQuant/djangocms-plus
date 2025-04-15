from django import forms
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLFormField

from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase
from cmsplus.cms_plugins.bootstrap.icon import IconField, IconPluginMixin
from cmsplus.cms_plugins.bootstrap.fields import SPACING_FIELD
from cmsplus.utils import strip_html_tags


class AccordionPluginForm(BootstrapFormBase):
    STYLE_CHOICES = 'ACCORDION_STYLES'

    icon = IconField(
        label=_("Icon"),
        initial="bi bi-chevron-down",
        required=False,
    )

    first_is_open = forms.BooleanField(
        label=_("First open"),
        initial=False,
        required=False,
        help_text=_("Start with the first item open.")
    )

    spacing = SPACING_FIELD


class AccordionPlugin(IconPluginMixin, BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap accordion.
    """
    name = "Accordion"
    form = AccordionPluginForm
    child_classes = ['AccordionItemPlugin']
    allow_children = True
    render_template = 'cmsplus/bootstrap/accordion/accordion.html'

    def render(self, context, instance, placeholder):
        instance.add_classes('accordion')
        instance.add_classes(instance.spacing)
        context.update({
            'first_is_open': instance.first_is_open
        })
        return super().render(context, instance, placeholder)


class AccordionItemForm(BootstrapFormBase):
    STYLE_CHOICES = 'ACCORDION_ITEM_STYLES'
    heading = HTMLFormField(label=_("Heading"))

class AccordionItemPlugin(BootstrapPluginBase):
    name = _("A. Item")
    form = AccordionItemForm
    parent_classes = ['AccordionPlugin']
    require_parent = True
    alien_child_classes = True
    allow_children = True
    render_template = 'cmsplus/bootstrap/accordion/accordion-item.html'

    @classmethod
    def get_identifier(cls, instance):
        heading = strip_html_tags(instance.glossary.get('heading', ''))
        return Truncator(heading).words(3, truncate=' ...')

    def render(self, context, instance, placeholder):
        instance.add_classes('accordion-item')
        context = super().render(context, instance, placeholder)

        parent_instance, _ = instance.parent.get_plugin_instance()
        context.update({
            'heading': mark_safe(instance.heading),
            'parent_instance': parent_instance,
        })
        return context
