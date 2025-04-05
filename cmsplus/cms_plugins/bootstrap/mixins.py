from django import forms
from django.utils.translation import gettext_lazy as _

from djangocms_link.fields import LinkFormField

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import PlusFilerImageSearchField
from cmsplus.utils import insert_fieldset
from cmsplus.cms_plugins.bootstrap.helper import get_img_dev_width_fields

# Background Image Mixins
# -----------------------
#
class BackgroundImageFormMixin(forms.Form):

    IMAGE_POSITIONING = (
        ("center center", _("Fully Centered")),
        ("left top", _("Top left")),
        ("center top", _("Top center")),
        ("right top", _("Top right")),
        ("left center", _("Center left")),
        ("right center", _("Center right")),
        ("left bottom", _("Bottom left")),
        ("center bottom", _("Bottom center")),
        ("right bottom", _("Bottom right")),
    )

    image = PlusFilerImageSearchField(
        label=_('Background Image'),
        required=False,
        help_text=_("If provided used as a cover for container."),
    )

    image_position = forms.ChoiceField(
        required=False,
        choices=IMAGE_POSITIONING,
        initial="center center",
        label=_("Background image position"),
    )

    image_filter = forms.ChoiceField(
        label='Image Filter', required=False,
        choices=cps.BGIMG_FILTER_CHOICES, initial='',
        help_text='The color filter to be applied over the unhovered image.')

    build_srcset = forms.BooleanField(
        label=_('Build Srcset'), initial=True, required=False,
        help_text=_('Build image srcset for the given device sizes below.'))

    upscale = forms.BooleanField(
        label=_('Upscale'), initial=False, required=False,
        help_text=_('Upscale image during scaling to given device size.'))

    crop = forms.BooleanField(
        label=_('Crop'), initial=False, required=False,
        help_text=_('Cut image before scale to given device size.'))

    crop_spec = forms.CharField(
        label=_('Crop Specifiaction'), initial='', required=False,
        help_text=_('Specifiy cropping, e.g.: smart | scale | 0,10 | ,0) - leave empty for default behavior.'))

    @classmethod
    def extend_form_fields(cls):
        for field_name, field in get_img_dev_width_fields():
            cls.declared_fields[field_name] = field


BackgroundImageFormMixin.extend_form_fields()

class BackgroundImagePluginMixin:

    image_fields = ['image', 'image_position', 'image_filter', 'build_srcset', 'upscale', 'crop', 'crop_spec'] + [
        field_name for field_name, _ in get_img_dev_width_fields()]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        new_fieldset = (
            "Image",
            {
                'classes': ['collapse'],
                'fields': (
                    ('image',),
                    ('image_position', 'image_filter', 'build_srcset'),
                    ('crop', 'upscale', 'crop_spec'),
                    [field_name for field_name, field in get_img_dev_width_fields()],
                ),
            }
        )
        return insert_fieldset(fieldsets, new_fieldset, 1, self.image_fields)

    @staticmethod
    def eval_background_image_props(instance):
        # shorty
        igg = instance.glossary.get

        if not igg('build_srcset', False):
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

    def render(self, context, instance, placeholder):
        if getattr(instance, "image", None):
            # class will be add as css in template
            instance.add_classes(f"background-image-{instance.id}")
            context.update(self.eval_background_image_props(instance))
        return super().render(context, instance, placeholder)
