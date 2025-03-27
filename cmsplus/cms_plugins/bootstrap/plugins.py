import logging
import urllib.parse

from django.utils.translation import gettext_lazy as _

from djangocms_frontend.contrib.grid.cms_plugins import GridContainerPlugin as GridContainerPluginBase
from djangocms_frontend.helpers import insert_fields, is_first_child
from djangocms_frontend.common import AttributesMixin, ResponsiveMixin, MarginMixin
from djangocms_frontend.contrib.link.cms_plugins import LinkPluginMixin

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.cms_plugins.bootstrap.models import PlusImage
from cmsplus.cms_plugins.bootstrap.forms import GridContainerForm, PlusImageForm, EmbedForm
from cmsplus.cms_plugins.bootstrap.helper import get_img_dev_width_field_names
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


# Embed Plugin
# ------------
#
class EmbedPlugin(BootstrapPluginBase):
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

    fieldsets = [
        (
            None,
            {
                "fields": (
                        'url',
                        'aspect_ratio',
                        'allow_fullscreen',
                        'autoplay',
                        'controls',
                        'loop',
                        'rel',
                )
            },
        ),
    ]

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
