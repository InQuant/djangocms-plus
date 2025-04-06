from django import forms
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLFormField

from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase
from cmsplus.utils import strip_html_tags


class AccordionPluginForm(BootstrapFormBase):
    STYLE_CHOICES = 'ACCORDION_STYLES'

    close_others = forms.BooleanField(
        label=_("Close others"),
        initial=True,
        required=False,
        help_text=_("Open only one card at a time.")
    )

    first_is_open = forms.BooleanField(
        label=_("First open"),
        initial=True,
        required=False,
        help_text=_("Start with the first card open.")
    )


class AccordionPlugin(BootstrapPluginBase):
    footnote_html = """
    Renders a bootstrap accordion.
    """
    name = "Accordion"
    form = AccordionPluginForm
    child_classes = ['AccordionGroupPlugin']
    allow_children = True
    render_template = 'cmsplus/bootstrap/accordion/accordion.html'

    def render(self, context, instance, placeholder):
        instance.add_classes('cmsplus-accordion')
        context.update({
            'close_others': instance.glossary.get('close_others', True),
            'first_is_open': instance.glossary.get('first_is_open', True),
        })
        return super().render(context, instance, placeholder)


class AccordionGroupForm(BootstrapFormBase):
    STYLE_CHOICES = 'ACCORDION_GROUP_STYLES'
    heading = HTMLFormField(label=_("Heading"))

class AccordionGroupPlugin(BootstrapPluginBase):
    name = _("A. Group")
    form = AccordionGroupForm
    parent_classes = ['AccordionPlugin']
    require_parent = True
    alien_child_classes = True
    allow_children = True
    render_template = 'cmsplus/bootstrap/accordion/accordion-group.html'

    @staticmethod
    def is_closed(instance, parent_instance):
        if instance.position == 0 and parent_instance.glossary.get('first_is_open'):
            return False
        elif not parent_instance.glossary.get('close_others'):
            return False
        return True

    @classmethod
    def get_identifier(cls, instance):
        heading = strip_html_tags(instance.glossary.get('heading', ''))
        return Truncator(heading).words(3, truncate=' ...')

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        parent_instance, _ = instance.parent.get_plugin_instance()
        instance.add_classes('cmsplus-accordion-head')

        context.update({
            'heading': mark_safe(instance.glossary.get('heading', '')),
            'parent_instance': parent_instance,
            'is_closed': self.is_closed(instance, parent_instance),
        })
        return context
