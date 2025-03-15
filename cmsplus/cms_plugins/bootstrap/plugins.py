import logging
import urllib.parse

from django import forms
from django.db.models import ManyToOneRel
from django.forms import widgets
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from entangled.forms import EntangledModelForm, EntangledModelFormMixin
from djangocms_frontend.contrib.grid.forms import GridContainerForm as GridContainerFormBase
from djangocms_frontend.contrib.grid.cms_plugins import GridContainerPlugin as GridContainerPluginBase
from djangocms_frontend.contrib.image.models import Image as FrontendImage
from djangocms_frontend.helpers import insert_fields, is_first_child
from djangocms_frontend import settings as fe_settings
from djangocms_frontend.common.attributes import AttributesMixin
from djangocms_frontend.common.responsive import ResponsiveMixin
from djangocms_frontend.common.spacing import MarginMixin
from djangocms_frontend.contrib.link.cms_plugins import LinkPluginMixin
from filer.fields.image import AdminImageFormField, FilerImageField

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import SizeField, PlusFilerImageSearchField
from cmsplus.forms import PlusStyleFormMixin, get_style_form_fields
from cmsplus.cms_plugins.bootstrap.models import PlusImage
from cmsplus.cms_plugins.bootstrap.forms import GridContainerForm, PlusImageForm
from cmsplus.cms_plugins.bootstrap.helper import get_img_dev_width_fields, get_img_dev_width_field_names, get_img_dev_width_mapping
from cmsplus.models import PlusItem
from cmsplus.plugin_base import PlusPlugin, StylePluginMixin

logger = logging.getLogger(__name__)


class BootstrapPluginBase(StylePluginMixin, PlusPlugin):
    module = 'Frontend'


class BackgroundImagePropertiesMixin():

    @staticmethod
    def eval_background_image_props(instance):
        # shorty
        igg = instance.glossary.get

        if not igg('do_thumbnail', False):
            return {}

        # scoped style background image widths
        bgimgwidths = {}
        ratio = igg('img_dev_width_xs') or '1/4'
        for dev in cps.DEVICES:
            width_key = 'img_dev_width_%s' % dev
            if igg(width_key):
                ratio = igg(width_key)
            k = cps.DEVICE_MIN_WIDTH_MAP.get(dev)
            w = cps.DEVICE_MAX_WIDTH_MAP.get(dev)
            # e.g. for md -> k=768, w=991, ratio=1/2: v = 991*1/2=496
            bgimgwidths[k] = '%dx0' % round(w * eval(ratio))

        if igg('crop', False) and igg('crop_spec', ''):
            crop = igg('crop_spec')  # smart or scale or 0,10 or ,10 ...
        else:
            crop = igg('crop')  # True or False

        return {
            'bgimgwidths': bgimgwidths,
            'crop': crop,  # boolean or str
        }


class GridContainerPlugin(
    StylePluginMixin,
    BackgroundImagePropertiesMixin,
    GridContainerPluginBase
):
    footnote_html = """
    Renders a bootstrap container fix or fluid for device classes of:
     <ul>
     <li>XS: Portrait Phones (<576px)</li>
     <li>SM: Small Tablets  (≥576px and <768px)</li>
     <li>MD: Tablets (≥768px and <992px)</li>
     <li>LG: Laptops (≥992px and <1.200px)</li>
     <li>XL: Desktops (≥1.200px and <1.600px)</li>
     <li>XXL: Large Desktops (≥1.600px and < 1.900px)</li>
     <ul>
    """
    form = GridContainerForm
    model = PlusItem
    allow_children = True
    parent_classes = None
    require_parent = False
    render_template = "cmsplus/bootstrap/container.html"

    def get_fieldsets(self, request, obj=None):
        """Extend the fieldset of the plugin to contain the new fields
        defined in forms.py"""
        return insert_fields(
            super().get_fieldsets(request, obj),
            (
                "image",
                (
                    "image_position",
                    "image_filter",
                ),
                (
                    "do_thumbnail",
                    "upscale",
                ),
                (
                    "crop",
                    "crop_spec",
                ),
                get_img_dev_width_field_names()
            ),
            block=None,  # Create a new fieldset (called block here)
            position=1,  # at position 1 (directly after the container fieldset)
            blockname=_("Image"),  # and call the fieldset "Image"
        )

    def render(self, context, instance, placeholder):
        if getattr(instance, "image", None):
            # class will be add as css in template
            instance.add_classes(f"container-image-{instance.id}")
            context.update(self.eval_background_image_props(instance))
        return super().render(context, instance, placeholder)

# Image
# -----
#

class ImagePlugin(
    StylePluginMixin,
    AttributesMixin,
    ResponsiveMixin,
    MarginMixin,
    LinkPluginMixin,
    PlusPlugin):

    footnote_html = """
        Renders a bootstrap responsive (fluid) image.
    """
    module = 'Frontend'
    model = PlusImage
    name = "Plus Image"
    form = PlusImageForm
    parent_classes = None
    require_parent = False

    text_enabled = True  # enable in text editor
    render_template = 'cmsplus/bootstrap/image.html'

    text_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-image" '
        'viewBox="0 0 16 16"><path d="M6.002 5.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"/>'
        '<path d="M2.002 1a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2zm12 1a1 1 0 0 1 1 '
        "1v6.5l-3.777-1.947a.5.5 0 0 0-.577.093l-3.71 3.71-2.66-1.772a.5.5 0 0 0-.63.062L1.002 12V3a1 1 0 0 1 "
        '1-1z"/></svg>'
    )

    #change_form_template = "djangocms_frontend/admin/image.html"

    fieldsets = [
        (
            None,
            {
                "fields": (
                    "picture",
                    (
                        "picture_fluid",
                        "lazy_loading",
                        "picture_rounded",
                        "picture_thumbnail",
                        *get_img_dev_width_field_names()
                    ),
                )
            },
        ),
        (
            _("Format"),
            {
                "classes": ("collapse",),
                "fields": (
                    ("width", "height"),
                    "alignment",
                ),
            },
        ),
        (
            _("Cropping"),
            {
                "classes": ("collapse",),
                "fields": (
                    ("use_crop", "use_upscale"),
                ),
            },
        ),
    ]
    link_fieldset_position = -1

    def render(self, context, instance, placeholder):
        if instance.config.get("lazy_loading", False):
            instance.add_attribute("loading", "lazy")
        # assign link to a context variable to be performant
        context["picture_link"] = instance.get_link()

        context["picture_size"] = instance.get_size(
            width=context.get("width", 0),
            height=context.get("height", 0),
        )
        
        # put srcset and srcset_sizes into context
        print('srcset: ', instance.srcset_data)
        context['srcset'] = instance.srcset_data.get('srcset', {})
        context['srcset_sizes'] = instance.srcset_data.get('srcset_sizes', [])

        if instance.alignment:
            # See https://getbootstrap.com/docs/5.2/content/images/#aligning-images
            instance.add_classes(instance.alignment)
        if instance.picture_fluid:
            instance.add_classes("img-fluid")
        if instance.picture_rounded:
            instance.add_classes("rounded")
        if instance.picture_thumbnail:
            instance.add_classes("img-thumbnail")
        if instance.parent and instance.parent.plugin_type == "CardPlugin":
            instance.add_classes("card-img-top" if is_first_child(instance, instance.parent) else "card-img-bottom")
        elif instance.parent and instance.parent.plugin_type == "FigurePlugin":
            instance.add_classes("figure-img")

        context = super().render(context, instance, placeholder)

        if not instance.picture:
            logger.error(_('Filer image not found for instance id: %s' % instance.id))
            return

        return context


'''

# Embed Plugin
# ------------
#
class EmbedForm(PlusStyleFormMixin):

    url = forms.URLField(
        label=_("Media URL"),
        widget=widgets.URLInput(attrs={'size': 50}),
        help_text=_(
            'Video Url to an external service w/o query params such as YouTube, Vimeo or others, ' 'e.g.: '
            'https://www.youtube.com/embed/vZw35VUBdzo'),
    )

    ASPECT_RATIO_CHOICES = [
        ('embed-responsive-21by9', _("Responsive 21:9")),
        ('embed-responsive-16by9', _("Responsive 16:9")),
        ('embed-responsive-4by3', _("Responsive 4:3")),
        ('embed-responsive-1by1', _("Responsive 1:1")),
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

    STYLE_CHOICES = 'EMBED_STYLES'
    extra_style, extra_classes, label, extra_css = get_style_form_fields(STYLE_CHOICES)


class BootstrapEmbedPlugin(BootstrapPluginBase):
    footnote_html = """
        Renders a bootstrap embed iframe for playing (e.g. youtube) videos.
        <br>
        It can be used with a modal popup or direct.
    """
    name = "Embed Video"
    allow_children = False
    form = EmbedForm
    render_template = 'cmsplus/bootstrap/embed.html'
    default_css_class = 'embed-responsive'
    css_class_fields = StylePluginMixin.css_class_fields + ['aspect_ratio']

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
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


# Button Plugin
# -------------
#
class BootstrapButtonForm(LinkFormBase):
    content = forms.CharField(
        label=_('Content'), required=False,
        help_text='Button content, e.g.: Click me, or nothing for icon only button')

    BUTTON_SIZES = [
        ('btn-lg', _("Large button")),
        ('', _("Default button")),
        ('btn-sm', _("Small button")),
    ]

    button_size = forms.ChoiceField(
        label=_("Button Size"),
        choices=BUTTON_SIZES,
        initial='',
        required=False,
        help_text=_("Button Size to use.")
    )

    button_block = forms.ChoiceField(
        label=_("Button Block"),
        choices=[
            ('', _('No')),
            ('btn-block', _('Block level button')),
        ],
        required=False,
        initial='',
        help_text=_("Use button block option (span left to right)?")
    )

    icon_position = forms.ChoiceField(
        label=_("Icon position"),
        choices=[
            ('icon-top', _("Icon top")),
            ('icon-right', _("Icon right")),
            ('icon-left', _("Icon left")),
        ],
        initial='icon-right',
        help_text=_("Select icon position related to content."),
    )

    icon = IconField(required=False)

    STYLE_CHOICES = 'BOOTSTRAP_BUTTON_STYLES'
    extra_style, extra_classes, label, extra_css = get_style_form_fields(STYLE_CHOICES)


class BootstrapButtonPluginModel(PlusItem, LinkPluginMixin):
    class Meta:
        proxy = True


class BootstrapButtonPlugin(StylePluginMixin, LinkPluginBase):
    footnote_html = """
        Renders a bootstrap button with various styles. The button may trigger a
        internal or external page link, a download oder mailto link.
    """
    module = 'Bootstrap'
    name = 'Button'
    parent_classes = None
    require_parent = False
    allow_children = False
    default_css_class = 'btn'
    render_template = 'cmsplus/bootstrap/button.html'

    form = BootstrapButtonForm
    model = BootstrapButtonPluginModel

    css_class_fields = StylePluginMixin.css_class_fields + ['button_size', 'button_block']

    class Media:
        css = {'all': ['cmsplus/admin/icon_plugin/css/icon_plugin.css'] + get_icon_style_paths()}
        js = ['cmsplus/admin/icon_plugin/js/icon_plugin.js']

    fieldsets = [
        (None, {
            'fields': ('content', ),
        }),
        (_('Styles'), {
            'fields': (
                ('extra_style', 'button_size', 'button_block'),
            ),
        }),
        (_('Link settings'), {
            'fields': (
                'link_type', 'cms_page', 'section', 'download_file', 'file_as_page', 'ext_url',
                'mail_to', 'link_target', 'link_title'
            )
        }),
        (_('Icon settings'), {
            'classes': ('collapse',),
            'fields': (
                'icon_position', 'icon',
            )
        }),
        (_('Extra settings'), {
            'classes': ('collapse',),
            'fields': (
                'extra_classes',
                'label',
            )
        }),
    ]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        icon_pos = instance.glossary.get('icon_position')
        icon = instance.glossary.get('icon')

        if icon:
            if icon_pos == 'icon-top':
                context['icon_top'] = format_html('&nbsp; <i class="{}"></i><br>'.format(icon))
            elif icon_pos == 'icon-left':
                context['icon_left'] = format_html('&nbsp; <i class="{}"></i>'.format(icon))
            elif icon_pos == 'icon-right':
                context['icon_right'] = format_html('&nbsp; <i class="{}"></i>'.format(icon))

        return context
'''