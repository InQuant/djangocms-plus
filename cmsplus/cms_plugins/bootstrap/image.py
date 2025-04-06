import logging
from django import forms
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import PlusFilerImageSearchField, PlusFilerFileSearchField, SizeField
from cmsplus.models import PlusItem
from cmsplus.forms import LinkFormMixin
from cmsplus.plugin_base import LinkPluginMixin
from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase
from cmsplus.cms_plugins.bootstrap.helper import get_img_dev_width_fields, get_img_dev_width_field_names
from cmsplus.utils import is_first_child, insert_fieldset

from easy_thumbnails.files import get_thumbnailer

logger = logging.getLogger(__name__)

class PlusImage(PlusItem):
    """
    Taken and adapted from djangocms_frontend.contrib
    Content > "Plus Image" Plugin
    https://getbootstrap.com/docs/5.0/content/images/
    """

    class Meta:
        proxy = True
        verbose_name = "Plus Image"

    image_field = "picture"

    def get_short_description(self):
        if self.picture:
            return self.picture.label or self.plugin_class.get_identifier(self)
        return _("<file is missing>")

    def is_gif(self):
        if self.picture and self.picture.extension == 'gif':
            return True
        return False
    
    @property
    def use_no_cropping(self):
        return not self.use_crop and not self.use_upscale

    @cached_property
    def img_src(self):
        # image can be empty, for example when the image is removed from filer
        # in this case we want to return an empty string to avoid #69
        if not self.picture:
            return ""
        # return the original, unmodified image
        elif self.use_no_cropping or self.is_gif:
            return self.picture.url if self.picture else ""

        picture_options = self.get_size(
            width=self.width or 0,
            height=self.height or 0,
        )

        thumbnail_options = {
            "size": picture_options["size"],
            "crop": picture_options["crop"],
            "upscale": picture_options["upscale"],
            "subject_location": self.rel_image.subject_location if self.rel_image else (),
        }

        try:
            thumbnailer = get_thumbnailer(self.rel_image)
            url = thumbnailer.get_thumbnail(thumbnail_options).url
        except ValueError:
            # get_thumbnailer() raises this if it can't establish a `relative_name`.
            # This may mean that the filer image has been deleted
            url = ""
        return url

    def get_size(self, width=None, height=None):
        crop = getattr(self, "use_crop", False)
        upscale = getattr(self, "use_upscale", False)

        if not getattr(self, "use_automatic_scaling", None):
            width = getattr(self, "width", None)
            height = getattr(self, "height", None)

        # calculate height when not given according to the
        # golden ratio or fallback to the image size
        picture_ratio = self.picture.width / self.picture.height if self.picture else cps.PICTURE_RATIO
        if not height and width:
            height = width / picture_ratio
        elif not width and height:
            width = height * picture_ratio
        elif not width and not height and getattr(self, "picture", None):
            if self.picture:
                width = self.picture.width
                height = self.picture.height
            else:
                width = 0
                height = 0
        elif not width and not height:  # pragma: no cover
            # If no information is available on the image size whatsoever,
            # make it 640px wide and use cps.PICTURE_RATIO
            width, height = 640, 640 / cps.PICTURE_RATIO
        width = int(width)
        height = int(height)
        return {
            "size": (width, height),
            "crop": crop,
            "upscale": upscale,
        }

    @cached_property
    def srcset_data(self):
        srcset_data = {}
        
        # no srcsets for gifs
        if self.is_gif():
            return srcset

        # prepare srcset
        media_queries, easy_thumb_sizes = self._get_media_sizes()

        # srcset sizes
        srcset_data['srcset_sizes'] = [media_queries[dev] for dev in cps.DEVICES]

        # srcset
        srcset = {}
        v = None
        for dev in cps.DEVICES:
            # e.g. srcset['320w'] = '320x200'
            k = '%dw' % easy_thumb_sizes[dev][0]
            v = '%dx%d' % (easy_thumb_sizes[dev][0], easy_thumb_sizes[dev][1])
            srcset[k] = v

        srcset_data['srcset'] = srcset
        # srcset_data['src_size'] = v

        return srcset_data

    def _get_media_sizes(self):
        """
        creates media_queries (srcset - sizes), e.g:

        media_queries = {
          'xs': '(max-width: 575.98px) 575px',
          'sm': '(max-width: 767.98px) 767px',
          'md': '(max-width: 991.98px) 496px',
          'lg': '(max-width: 1199.98px) 600px',
          'xl': '800px'}

        and the img sizes for easythumbnail, e.g:

        easythumb_sizes = {
          'xs': (575, 0),
          'sm': (767, 0),
          ...
        }.
        """
        glossary = self.glossary

        # img_dev_width_* contains '1/2' or '1/3' (of screen size)
        dev_img_fraction = eval(glossary.get('img_dev_width_xs'))
        fixed_size = {
            'width': glossary.get('fixed_width_xs'), 'height':
                glossary.get('fixed_height_xs')}

        queries = {}  # for srcset sizes
        ets = {}  # easythumb_sizes
        for dev in cps.DEVICES:

            # inherits from xs or other value for higher device
            _dev_img_fraction = glossary.get('img_dev_width_%s' % dev)
            if _dev_img_fraction:
                dev_img_fraction = eval(_dev_img_fraction)

            dev_max_w = cps.DEVICE_MAX_WIDTH_MAP.get(dev)
            ets[dev] = self._compute_thumb_size(
                glossary.get('picture'), dev_max_w,
                dev_img_fraction, fixed_size)

            if dev != 'xl':
                queries[dev] = '(max-width: %.2fpx) %.2fpx' % (dev_max_w, ets[dev][0])
            else:
                queries[dev] = '%.2fpx' % ets[dev][0]

        return queries, ets

    def _compute_thumb_size(self, image, dev_max_width, dev_img_fraction, given_fixed_size):

        def _compute_aspect_ratio(_image):
            if _image.exif.get('Orientation', 1) > 4:
                # image is rotated by 90 degrees, while keeping width and height
                return float(_image.width) / float(_image.height)
            else:
                return float(_image.height) / float(_image.width)

        def _clean_w(width):
            if width > dev_max_width:
                return dev_max_width
            return round(width)

        if not image:
            return

        aspect_ratio = _compute_aspect_ratio(image)
        fallback_width = round(dev_max_width * dev_img_fraction)

        g_w = given_fixed_size['width']
        g_h = given_fixed_size['height']

        gnp = SizeField.get_number_part
        if g_w and g_h:
            # fixed width **and** height given

            if 'px' in g_w and 'px' in g_h:
                # both are in px
                return _clean_w(gnp(g_w)), round(gnp(g_h))
            elif 'px' in g_w:
                # width in px
                return _clean_w(gnp(g_w)), 0
            elif 'px' in g_h:
                # height in px
                h = gnp(g_h)
                return round(h / aspect_ratio), round(h)
            else:
                # fallback dev_max_width * fraction
                return fallback_width, 0

        elif g_w:
            # fixed width given
            if 'px' in g_w:
                # width in px
                return _clean_w(gnp(g_w)), 0
            else:
                # fallback dev_max_width * fraction
                return fallback_width, 0

        elif g_h:
            # fixed height given
            if 'px' in g_h:
                # height in px
                h = gnp(g_h)
                return round(h / aspect_ratio), round(h)
            else:
                # fallback dev_max_width * fraction
                return fallback_width, 0
        else:
            # no fixed
            return fallback_width, 0


class ImageFormMixin(forms.Form):

    picture = PlusFilerImageSearchField(label=_('Image File'), required=True)

    lazy_loading = forms.BooleanField(
        label=_("Load lazily"),
        required=False,
        initial=True,
        help_text=_("Use for images below the fold. This will load images only if user scrolls them into view. "),
    )
    width = forms.IntegerField(
        label=_("Width"),
        required=False,
        min_value=1,
        help_text=_("The image width as number in pixels. " 'Example: "720" and not "720px".'),
    )
    height = forms.IntegerField(
        label=_("Height"),
        required=False,
        min_value=1,
        help_text=_("The image height as number in pixels. " 'Example: "720" and not "720px".'),
    )

    ALIGNMENT_OPTIONS = [
        ('', _("None")),
        ('float-start', _("Left")),
        ('float-end', _("Right")),
        ('mx-auto d-block', _("Center")),
    ]
    alignment = forms.ChoiceField(
        label=_("Alignment"),
        choices=ALIGNMENT_OPTIONS,
        initial='',
        required=False,
        help_text=_("Aligns the image according to the selected option."),
    )

    # upscale and crop work together
    # throws validation error if other cropping options are selected
    use_crop = forms.BooleanField(
        label=_("Crop image"),
        required=False,
        help_text=_("Crops the image according to the thumbnail settings provided in the template."),
    )
    use_upscale = forms.BooleanField(
        label=_("Upscale image"),
        required=False,
        help_text=_("Upscales the image to the size of the thumbnail settings in the template."),
    )
    picture_fluid = forms.BooleanField(
        label=_("Responsive"),
        required=False,
        initial=True,
        help_text=_("Adds the .img-fluid class to make the image responsive."),
    )
    picture_rounded = forms.BooleanField(
        label=_("Rounded"),
        required=False,
        initial=False,
        help_text=_("Adds the .rounded class for round corners."),
    )
    picture_thumbnail = forms.BooleanField(
        label=_("Thumbnail"),
        required=False,
        initial=False,
        help_text=_("Adds the .img-thumbnail class."),
    )

    @classmethod
    def extend_form_fields(cls):
        for field_name, field in get_img_dev_width_fields():
            cls.declared_fields[field_name] = field


ImageFormMixin.extend_form_fields()


class PlusImageForm(LinkFormMixin, ImageFormMixin, BootstrapFormBase):
    """
    Content > "Image" Plugin
    https://getbootstrap.com/docs/5.0/content/images/
    """

    link_is_optional = True
    STYLE_CHOICES = 'MOD_IMAGE_STYLES' # for PlusStyleEntangledFormMixin


class ImagePlugin(LinkPluginMixin, BootstrapPluginBase):
    footnote_html = """
        Renders a bootstrap responsive (fluid) image.
    """
    name = "Image"
    model = PlusImage
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

    image_fieldsets = [
        (
            None,
            {
                "fields": (
                    ("picture",),
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
    link_fieldset_index = 2

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        keys_to_remove = self.form.base_fields.keys()
        for index, fs in enumerate(self.image_fieldsets):
            fieldsets = insert_fieldset(fieldsets, fs, index, keys_to_remove)
        return fieldsets

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


# SVG Image
# ---------
#
class SvgImageForm(LinkFormMixin, BootstrapFormBase):

    picture = PlusFilerFileSearchField(
        label=_('SVG Image File'),
        required=True,
    )

    require_link = False
    STYLE_CHOICES = 'SVG_STYLES'


class SvgImagePlugin(LinkPluginMixin, BootstrapPluginBase):
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
