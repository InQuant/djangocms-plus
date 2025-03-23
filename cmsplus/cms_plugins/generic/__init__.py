import sys

from django import forms
from django import template
from django.forms import widgets
from django.template.context import Context
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import SizeField, PlusFilerFileSearchField
from cmsplus.forms import (PlusPluginFormBase, get_style_form_fields, AbstractLinkForm)
from cmsplus.plugin_base import StylePluginMixin, PlusPlugin, LinkPluginMixin

# MultiColTextPlugin
# ------------------
#
class MultiColTextForm(PlusPluginFormBase):
    STYLE_CHOICES = 'MOD_COL_STYLES'
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)

    @staticmethod
    def _get_col_choice_field(dev):
        if dev == 'xs':
            choices = [('', '1 (default)'), ]
        else:
            choices = [('', 'inherit'), ]
        choices.extend(list(cps.TX_COL_CHOICES))

        field_name = 'col_%s' % dev
        field = forms.ChoiceField(
            label=u'%s No. of Cols' % cps.DEVICE_MAP[dev], required=False, choices=choices, initial='')
        return field_name, field

    @classmethod
    def extend_col_fields(cls):
        for dev in cps.DEVICES:
            field_name, field = cls._get_col_choice_field(dev)
            cls.declared_fields[field_name] = field


MultiColTextForm.extend_col_fields()


class MultiColumnTextPlugin(StylePluginMixin, PlusPlugin):
    footnote_html = """
    renders a wrapper for a multi column text.
    """
    name = 'MultiColumnText'
    form = MultiColTextForm
    render_template = "cmsplus/generic/multi-col-text.html"
    allow_children = True

    fieldsets = [
        (
            None,
            {
                "fields": (
                        ('col_xs', 'col_sm'),
                        ('col_md', 'col_lg'),
                        ('col_xl', 'col_xxl',),
                )
            },
        ),
    ]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        for dev in cps.DEVICES:
            v = getattr(instance, f'col_{dev}')
            print('***', dev, v)
            if v: instance.add_classes(f'c-text-col-{v}')
        return context


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
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)


class SnippetPlugin(StylePluginMixin, PlusPlugin):
    footnote_html = """
    renders a given html snippet, can be used to include another site via iframe.
    """
    name = 'Snippet'
    form = SnippetForm
    allow_children = False
    render_template = 'cmsplus/generic/snippet/snippet.html'
    change_form_template = 'cmsplus/generic/snippet/change_form.html'

    text_enabled = True
    text_editor_preview = False

    fieldsets = [
        (
            None,
            {
                "fields": ('html',),
            },
        ),
    ]

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


# SVG Plugin
# ----------
#
class SvgImageForm(AbstractLinkForm):

    picture = PlusFilerFileSearchField(
        label=_('SVG Image File'),
        required=True,
    )

    require_link = False
    STYLE_CHOICES = 'SVG_STYLES'
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)


class SvgImagePlugin(StylePluginMixin, LinkPluginMixin, PlusPlugin):
    footnote_html = """
    renders a svg in an image tag.
    """
    name = 'SvgImage'
    form = SvgImageForm
    allow_children = False
    render_template = 'cmsplus/generic/svg.html'

    text_enabled = True  # enable in TEXT Plugin EDITOR
    text_editor_preview = False
    tag_attr_map = {'image_title': 'title', 'image_alt': 'alt'}

    fieldsets = [
        (None, {
            'fields': ('picture',),
        })
    ]

'''

# VerticalRatioSpacer Plugin
# --------------------------
#
class VerticalRatioSpacerForm(PlusPluginFormBase):

    landscape_height = SizeField(
        label=_('Height for landscape screen ratio.'),
        required=True,
        allowed_units=['px', '%', 'rem', 'vw', 'vh'],
        initial='',
    )
    portrait_height = SizeField(
        label=_('Height for portrait screen ratio.'),
        required=True,
        allowed_units=['px', '%', 'rem', 'vw', 'vh'],
        initial='',
    )

    STYLE_CHOICES = 'VERTICAL_RATIO_SPACER_STYLES'
    extra_style, extra_classes, label, extra_css = get_style_form_fields(STYLE_CHOICES)


class VerticalRatioSpacerPlugin(StylePluginMixin, PlusPluginBase):
    footnote_html = """
    renders a vertical spacer (div), where a ratio depending height can be given.
    """
    name = 'VerticalRatioSpacer'
    form = VerticalRatioSpacerForm
    allow_children = True
    render_template = 'cmsplus/generic/vertical-ratio-spacer.html'
    tag_type = 'div'

    @classmethod
    def get_css_classes(cls, instance):
        """
        add the c-vertical-ratio-spacer-<id> class to be able to identify the div element in js.
        """
        css_classes = super().get_css_classes(instance)
        css_classes.append('c-vertical-ratio-spacer-%s' % instance.id)
        return css_classes


# Background Video
# ----------------
#
class BackgroundVideoForm(PlusPluginFormBase):

    video_file = PlusFilerFileSearchField(
        label='Video file',
        help_text=_("An internal link onto an video file"),
    )

    image_filter = forms.ChoiceField(
        label='Image Filter', required=False,
        choices=cps.BGIMG_FILTER_CHOICES, initial='',
        help_text='The color filter to be applied over the unhovered video.')

    bottom_margin = forms.ChoiceField(
        label=u'Bottom Margin',
        required=False, choices=cps.CNT_BOTTOM_MARGIN_CHOICES,
        initial='',
        help_text='Select the default bottom margin to be applied?')

    STYLE_CHOICES = 'BACKGROUND_VIDEO_STYLES'
    extra_style, extra_classes, label, extra_css = get_style_form_fields(STYLE_CHOICES)


class BackgroundVideoPlugin(StylePluginMixin, PlusPluginBase):
    name = "Background Video"
    allow_children = True
    admin_preview = False
    form = BackgroundVideoForm
    render_template = 'cmsplus/generic/background-video.html'

    css_class_fields = StylePluginMixin.css_class_fields + ['bottom_margin']

    fieldsets = [
        (None, {
            'fields': ('video_file', 'image_filter', 'bottom_margin'),
        }),
        (_('Module settings'), {
            'fields': (
                'extra_style', 'extra_classes', 'label',
            )
        }),
    ]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        video = instance.glossary.get('video_file', None)
        if video:
            context['video_url'] = video.url
        return context


class AudioEmbedForm(PlusPluginFormBase):
    src = forms.CharField(
        label=_("Audio URL"),
        widget=widgets.Input(),
        help_text=_(
            'Audio URL to an external audio file e.g.: '
            'https://www.example.com/sample.mp3'),
    )

    figcaption = forms.CharField(
        label=_('Figcaption for Audio'),
        required=False,
    )

    controls = forms.BooleanField(
        label=_("Display Controls"),
        required=False,
        initial=True,
    )

    muted = forms.BooleanField(
        label=_("Start muted"),
        required=False,
    )

    autoplay = forms.BooleanField(
        label=_("Autoplay"),
        required=False,
        help_text=_('Will be blocked by browser by default.')
    )

    loop = forms.BooleanField(
        label=_("Enable Looping"),
        required=False,
        help_text=_('Inifinte loop playing.'),
    )


class AudioEmbedPlugin(StylePluginMixin, PlusPluginBase):
    name = 'Embed Audio'
    form = AudioEmbedForm
    render_template = 'cmsplus/generic/audio-embed.html'
    footnote_html = """Renders HTML Audioplayer from a playable file url. 
"""

'''