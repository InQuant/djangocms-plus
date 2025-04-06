import sys

from django import forms
from django import template
from django.template.context import Context
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from cmsplus.forms import PlusPluginFormBase
from cmsplus.plugin_base import PlusPlugin


# Snippet Plugin
# --------------
#
class SnippetForm(PlusPluginFormBase):

    html = forms.CharField(
        label=_('HTML'),
        widget=forms.Textarea(
            attrs={
                'rows': 15, 'data-editor': True,
                'data-mode': 'html', 'data-theme': 'default',
                'style': 'max-height: initial', 'class': 'c-border'}),
    )

    STYLE_CHOICES = 'SNIPPET_STYLES'


class SnippetPlugin(PlusPlugin):
    footnote_html = """
    renders a given html snippet, can be used to include another site via iframe.
    """
    name = 'Snippet'
    form = SnippetForm
    allow_children = True
    render_template = 'cmsplus/generic/snippet/snippet.html'
    change_form_template = 'cmsplus/generic/snippet/change_form.html'

    text_enabled = True
    text_editor_preview = False

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.html)

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        try:
            t = template.Template(instance.glossary.get('html'))
            content = t.render(Context(context))
        except Exception:
            exc = sys.exc_info()[0]
            content = str(exc)
        context['content'] = mark_safe(content)
        return context
