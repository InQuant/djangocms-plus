import logging

from django import forms
from django.forms import widgets
from django.utils.translation import gettext_lazy as _

from entangled.forms import EntangledModelForm, EntangledModelFormMixin
from djangocms_frontend.contrib.grid.forms import GridContainerForm as GridContainerFormBase
from djangocms_frontend import settings as fe_settings
from djangocms_frontend.common import ResponsiveFormMixin, MarginFormMixin
from djangocms_frontend.fields import AttributesFormField, TagTypeFormField
from djangocms_frontend.contrib.link.forms import AbstractLinkForm

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.fields import PlusFilerImageSearchField
from cmsplus.forms import PlusPluginFormBase, PlusStyleEntangledFormMixin, get_style_form_fields
from cmsplus.cms_plugins.bootstrap.helper import get_img_dev_width_fields, get_img_dev_width_field_names
from cmsplus.models import PlusItem
from cmsplus.cms_plugins.bootstrap.models import PlusImage

logger = logging.getLogger(__name__)


# GridContainer
# -------------
#
class GridContainerFormMixin(PlusStyleEntangledFormMixin, EntangledModelFormMixin):
    STYLE_CHOICES = 'MOD_CONTAINER_STYLES' # for PlusStyleEntangldFormMixin

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
        choices=fe_settings.EMPTY_CHOICE + IMAGE_POSITIONING,
        initial="",
        label=_("Background image position"),
    )

    image_filter = forms.ChoiceField(
        label='Image Filter', required=False,
        choices=cps.BGIMG_FILTER_CHOICES, initial='',
        help_text='The color filter to be applied over the unhovered image.')

    do_thumbnail = forms.BooleanField(
        label=_('Do thumbnail'), initial=True, required=None,
        help_text=_('Scale (thumbnail) image according to given device sizes below.'))

    upscale = forms.BooleanField(
        label=_('Upscale'), initial=False, required=False,
        help_text=_('Upscale image during scaling to given device size.'))

    crop = forms.BooleanField(
        label=_('Crop'), initial=True, required=False,
        help_text=_('Cut image before scale to given device size.'))

    crop_spec = forms.CharField(
        label=_('Crop Specifiaction'), initial='', required=False,
        help_text=_('Specifiy cropping, e.g.: smart | scale | 0,10 | ,0) - leave empty for default behavior.'))


    class Meta:
        entangled_fields = {
            "config": [
                "image",
                "image_position",
                "image_filter",
                "do_thumbnail",
                "upscale",
                "crop",
                "crop_spec",
            ]
        }

    def __init_subclass__(cls, **kwargs):
        """ extend fields with image width fields
        """
        super().__init_subclass__(**kwargs)
        cls.declared_fields.update(dict(get_img_dev_width_fields()))
        cls._meta.entangled_fields['config'].extend(get_img_dev_width_field_names())

class GridContainerForm(GridContainerFormMixin, GridContainerFormBase):
    class Meta:
        model = PlusItem
        entangled_fields = {
            "config": []
        }

# Image Form
# ----------
#

class PlusImageFormMixin(EntangledModelFormMixin):

    picture = PlusFilerImageSearchField(label=_('Image File'), required=True)

    lazy_loading = forms.BooleanField(
        label=_("Load lazily"),
        required=False,
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
    link_attributes = AttributesFormField(
        label=_("Link attributes"),
        help_text=_("Attributes apply to the <b>link</b>."),
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
    tag_type = TagTypeFormField()

    class Meta:
        entangled_fields = {
            "config": [
                "picture",
                "lazy_loading",
                "width",
                "height",
                "alignment",
                "link_attributes",
                "use_crop",
                "use_upscale",
                "picture_fluid",
                "picture_rounded",
                "picture_thumbnail",
            ]
        }

    def __init_subclass__(cls, **kwargs):
        """ extend fields with image width fields
        """
        super().__init_subclass__(**kwargs)
        cls.declared_fields.update(dict(get_img_dev_width_fields()))
        cls._meta.entangled_fields['config'].extend(get_img_dev_width_field_names())


class PlusImageForm(
    PlusStyleEntangledFormMixin, 
    AbstractLinkForm,
    ResponsiveFormMixin,
    MarginFormMixin,
    PlusImageFormMixin,
    EntangledModelForm,
):
    """
    Content > "Image" Plugin
    https://getbootstrap.com/docs/5.0/content/images/
    """

    link_is_optional = True

    STYLE_CHOICES = 'MOD_IMAGE_STYLES' # for PlusStyleEntangledFormMixin

    class Meta:
        model = PlusImage
        entangled_fields = {
            "config": []
        }

    def clean(self):
        super().clean()
        data = self.cleaned_data
        # there can be only one link type
        if (
            sum(
                (
                    bool(data.get("external_link", False)),
                    bool(data.get("internal_link", False)),
                    bool(data.get("file_link", False)),
                )
            )
            > 1
        ):
            raise forms.ValidationError(
                _(
                    "You have given more than one external, internal, or file link target. "
                    "Only one option is allowed."
                )
            )


# Embed Form
# ----------
#
class EmbedForm(PlusPluginFormBase):
    STYLE_CHOICES = 'EMBED_STYLES'
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)

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
