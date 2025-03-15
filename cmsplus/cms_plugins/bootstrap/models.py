import logging
import urllib.parse

from django.conf import settings
from django import forms
from django.utils.functional import cached_property
from django.db.models import ManyToOneRel
from django.forms import widgets
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from djangocms_frontend.models import FrontendUIItem
from djangocms_frontend.contrib.grid.forms import GridContainerForm as GridContainerFormBase
from djangocms_frontend.contrib.grid.cms_plugins import GridContainerPlugin as GridContainerPluginBase
from djangocms_frontend.contrib.image.forms import ImageForm as ImageFormBase
from djangocms_frontend.contrib.link.models import GetLinkMixin
from djangocms_frontend.helpers import insert_fields
from djangocms_frontend import settings as fe_settings
from easy_thumbnails.files import get_thumbnailer
from entangled.forms import EntangledModelForm, EntangledModelFormMixin
from filer.fields.image import AdminImageFormField, FilerImageField

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import SizeField, PlusFilerImageSearchField
from cmsplus.forms import PlusStyleFormMixin, get_style_form_fields
from cmsplus.cms_plugins.bootstrap.helper import get_img_dev_width_fields, get_img_dev_width_field_names
from cmsplus.models import PlusItem, PlusItemMixin
from cmsplus.plugin_base import PlusPlugin, StylePluginMixin

logger = logging.getLogger(__name__)

# use golden ration as default (https://en.wikipedia.org/wiki/Golden_ratio)
PICTURE_RATIO = getattr(settings, "DJANGOCMS_PICTURE_RATIO", 1.6180)

class PlusImage(PlusItemMixin, GetLinkMixin, FrontendUIItem):
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
        if self.picture and self.picture.label:
            return self.picture.label
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
        picture_ratio = self.picture.width / self.picture.height if self.picture else PICTURE_RATIO
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
            # make it 640px wide and use PICTURE_RATIO
            width, height = 640, 640 / PICTURE_RATIO
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

    '''
    @cached_property
    def img_srcset_data(self):
        if not self.picture:
            return None

        srcset = []

        try:
            thumbnailer = get_thumbnailer(self.picture)

            picture_options = self.get_size(self.width, self.height)
            picture_width = picture_options["size"][0]
            thumbnail_options = {"crop": picture_options["crop"]}
            breakpoints = getattr(
                settings,
                "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_VIEWPORT_BREAKPOINTS",
                [576, 768, 992],
            )

            for size in filter(lambda x: x < picture_width, breakpoints):
                thumbnail_options["size"] = (size, size)
                srcset.append((int(size), thumbnailer.get_thumbnail(thumbnail_options)))
        except ValueError:
            # get_thumbnailer() raises this if it can't establish a `relative_name`.
            # This may mean that the filer image has been deleted
            pass

        return srcset

    @cached_property
    def img_src(self):
        # image can be empty, for example when the image is removed from filer
        # in this case we want to return an empty string to avoid #69
        if not self.picture:
            return ""
        # return the original, unmodified image
        elif self.use_no_cropping:
            return self.picture.url if self.picture else ""

        picture_options = self.get_size(
            width=self.width or 0,
            height=self.height or 0,
        )

        thumbnail_options = {
            "size": picture_options["size"],
            "crop": picture_options["crop"],
            "upscale": picture_options["upscale"],
            "subject_location": self.picture.subject_location if self.picture else (),
        }

        try:
            thumbnailer = get_thumbnailer(self.picture)
            url = thumbnailer.get_thumbnail(thumbnail_options).url
        except ValueError:
            # get_thumbnailer() raises this if it can't establish a `relative_name`.
            # This may mean that the filer image has been deleted
            url = ""
        return url

    def get_size(self, width=None, height=None):
        crop = getattr(self, "use_crop", False)
        upscale = getattr(self, "use_upscale", False)
        # use field thumbnail settings
        if getattr(self, "thumbnail_options", None):
            thumbnail_options = get_related_object(self.config, "thumbnail_options")
            width = thumbnail_options.width
            height = thumbnail_options.height
            crop = thumbnail_options.crop
            upscale = thumbnail_options.upscale
        elif not getattr(self, "use_automatic_scaling", None):
            width = getattr(self, "width", None)
            height = getattr(self, "height", None)

        # calculate height when not given according to the
        # golden ratio or fallback to the image size
        picture_ratio = self.picture.width / self.picture.height if self.picture else PICTURE_RATIO
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
            # make it 640px wide and use PICTURE_RATIO
            width, height = 640, 640 / PICTURE_RATIO
        width = int(width)
        height = int(height)
        return {
            "size": (width, height),
            "crop": crop,
            "upscale": upscale,
        }
    '''