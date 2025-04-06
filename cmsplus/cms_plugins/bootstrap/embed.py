import urllib.parse
from django import forms
from django.forms import widgets
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import AttributesFormField, PlusFilerFileSearchField
from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase

# Embed Plugin
# ------------
#
class VideoForm(BootstrapFormBase):
    STYLE_CHOICES = 'EMBED_STYLES'

    url = forms.URLField(
        label=_("Media URL"),
        widget=widgets.URLInput(attrs={'size': 50}),
        help_text=_(
            'Video Url to an external service w/o query params such as YouTube, Vimeo or others, ' 'e.g.: '
            'https://www.youtube.com/embed/vZw35VUBdzo'),
    )

    ASPECT_RATIO_CHOICES = [
        ('ratio ratio-21x9', _("Responsive 21:9")),
        ('ratio ratio-16x9', _("Responsive 16:9")),
        ('ratio ratio-4x3', _("Responsive 4:3")),
        ('ratio ratio-1x1', _("Responsive 1:1")),
    ]
    aspect_ratio = forms.ChoiceField(
        label=_("Aspect Ratio"),
        choices=ASPECT_RATIO_CHOICES,
        widget=widgets.RadioSelect,
        required=False,
        initial=ASPECT_RATIO_CHOICES[1][0],
    )

    allow_fullscreen = forms.BooleanField(
        label=_("Allow Fullscreen"),
        required=False,
        initial=True,
    )

    autoplay = forms.BooleanField(
        label=_("Autoplay"),
        required=False,
    )

    controls = forms.BooleanField(
        label=_("Display Controls"),
        required=False,
    )

    loop = forms.BooleanField(
        label=_("Enable Looping"),
        required=False,
        help_text=_('Inifinte loop playing.'),
    )

    rel = forms.BooleanField(
        label=_("Show related"),
        required=False,
        help_text=_('Show related media content'),
    )

    attributes = AttributesFormField()

class VideoPlugin(BootstrapPluginBase):
    footnote_html = """
        Renders a bootstrap embed iframe for playing (e.g. youtube) videos.
        <br>
        It can be used with a modal popup or direct.
    """
    name = "Video"
    allow_children = False
    form = VideoForm
    render_template = 'cmsplus/bootstrap/video.html'
    default_css_class = 'embed-responsive'

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.url)

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        instance.add_classes(instance.aspect_ratio, self.default_css_class)

        url = instance.glossary.get('url')
        params = {}
        for k in ['autoplay', 'controls', 'loop', 'rel']:
            if instance.glossary.get(k):
                params[k] = instance.glossary.get(k)

        q = urllib.parse.urlencode(params)
        context.update({
            'embed_url': '%s?%s' % (url, q),
            'allowfullscreen': 'allowfullscreen' if instance.glossary.get('allow_fullscreen') else '',
        })
        return context


# Background Video
# ----------------
#
class BackgroundVideoForm(BootstrapFormBase):

    video_file = PlusFilerFileSearchField(
        label='Video file',
        help_text=_("An internal link onto an video file"),
    )

    image_filter = forms.ChoiceField(
        label='Image Filter', required=False,
        choices=cps.BGIMG_FILTER_CHOICES, initial='',
        help_text='The color filter to be applied over the unhovered video.')

    STYLE_CHOICES = 'BACKGROUND_VIDEO_STYLES'


class BackgroundVideoPlugin(BootstrapPluginBase):
    name = "Background Video"
    allow_children = True
    admin_preview = False
    form = BackgroundVideoForm
    render_template = 'cmsplus/bootstrap/background-video.html'

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        instance.add_classes('position-relative overflow-hidden')
        video = instance.glossary.get('video_file', None)
        if video:
            context['video_url'] = video.url
        return context


# Background Video
# ----------------
#
class AudioEmbedForm(BootstrapFormBase):
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


class AudioEmbedPlugin(BootstrapPluginBase):
    footnote_html = 'Renders HTML Audioplayer from a playable file url.'
    name = 'Embed Audio'
    form = AudioEmbedForm
    render_template = 'cmsplus/bootstrap/audio-embed.html'
