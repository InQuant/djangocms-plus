from django.conf import settings

from cmsplus.utils import JSONEncoder

class CmsPlusSettings:

    PLUGINS = (
        'cmsplus.cms_plugins.bootstrap.link.LinkPlugin',
        'cmsplus.cms_plugins.bootstrap.icon.IconPlugin',
        'cmsplus.cms_plugins.bootstrap.grid.SpacerPlugin',
        'cmsplus.cms_plugins.bootstrap.grid.GridContainerPlugin',
        'cmsplus.cms_plugins.bootstrap.grid.GridRowPlugin',
        'cmsplus.cms_plugins.bootstrap.grid.GridColumnPlugin',
        'cmsplus.cms_plugins.bootstrap.image.ImagePlugin',
        'cmsplus.cms_plugins.bootstrap.image.SvgImagePlugin',
        'cmsplus.cms_plugins.bootstrap.embed.VideoPlugin',
        'cmsplus.cms_plugins.generic.multicoltext.MultiColumnTextPlugin',
        'cmsplus.cms_plugins.bootstrap.embed.BackgroundVideoPlugin',
        'cmsplus.cms_plugins.bootstrap.embed.AudioEmbedPlugin',

        'cmsplus.cms_plugins.generic.snippet.SnippetPlugin',
        'cmsplus.cms_plugins.generic.slider.SlidePlugin',
        'cmsplus.cms_plugins.generic.slider.SliderPlugin',
    )

    EMPTY_CHOICE = (("", "-----"),)

    JSON_ENCODER_CLASS = JSONEncoder

    MAP_LAYER_CHOICES = (
        ('', 'None'),
        ('stamen', 'Stamen'),
        ('black', 'Black'),
    )

    DEVICES = ('xs', 'sm', 'md', 'lg', 'xl', 'xxl')
    DEVICE_MAP = {'xs': 'phone', 'sm': 'tablet small', 'md': 'tablet', 'lg': 'desktop', 'xl': 'desktop xl', 'xxl': 'desktop xxl',  }
    DEVICE_MAX_WIDTH_MAP = {'xs': 575, 'sm': 767, 'md': 991, 'lg': 1199, 'xl': 1399, 'xxl': 1899,  }
    DEVICE_MIN_WIDTH_MAP = {'xs': 0, 'sm': 576, 'md': 768, 'lg': 992, 'xl': 1200, 'xxl': 1400 }

    SPACING_VALUE_LIMIT = 5

    COLOR_CHOICES = (
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
    )

    TX_COL_CHOICES = (
        ('2', '2 Text Columns'),
        ('3', '3 Text Columns'),
        # remember to inc col no in scss
    )

    # use golden ration as default (https://en.wikipedia.org/wiki/Golden_ratio)
    PICTURE_RATIO = 1.6180
    IMG_DEV_WIDTH_CHOICES = (
        ('1', 'full screen'),
        ('3/4', '3/4 screen'),
        ('2/3', '2/3 screen'),
        ('1/2', '1/2 screen'),
        ('1/3', '1/3 screen'),
        ('1/4', '1/4 screen'),
        ('1/5', '1/5 screen'),
        ('1/6', '1/6 screen'),
    )

    BGIMG_FILTER_CHOICES = (
        ('', 'None'),
        ('linear-gradient(to top, rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0))', 'black top')
    )

    # show and hide icons in project
    ICONS_FONTAWESOME_SHOW = False
    ICONS_FONTAWESOME = {
        'meta': 'cmsplus/icons/fontawesome/metadata/icons.json',
        'css': 'cmsplus/icons/fontawesome/css/all.css',
    }

    BOOTSTRAP_CSS = 'frontend/node_modules/bootstrap/dist/css/bootstrap.min.css'
    BOOTSTRAP_JS = 'frontend/node_modules/bootstrap/dist/js/bootstrap.min.js'

    # https://github.com/twbs/icons
    ICONS_BOOTSTRAP_SHOW = True
    ICONS_BOOTSTRAP = {
        'meta': 'frontend/node_modules/bootstrap-icons/font/bootstrap-icons.json',
        'css': 'frontend/node_modules/bootstrap-icons/font/bootstrap-icons.css',
    }

    # custom fontello font packs
    ICONS_FONTELLO = [
        # { 'meta': '', 'css': '' }
    ]

    MAGIC_WRAPPER_STYLES = (
        ('', 'None'),
    )

    MOD_CONTAINER_STYLES = (
        ('', 'None'),
    )

    MOD_ROW_STYLES = (
        ('', 'None'),
    )

    MOD_COL_STYLES = (
        ('', 'None'),
    )

    IMAGE_STYLES = (
        ('', 'None'),
    )

    BACKGROUND_IMAGE_STYLES = (
        ('', 'None'),
    )

    CARD_STYLES = (
        ('', 'Default'),
    )
    CARD_HEADER_STYLES = (
        ('', 'Default'),
    )
    CARD_BODY_STYLES = (
        ('', 'Default'),
    )
    CARD_FOOTER_STYLES = (
        ('', 'Default'),
    )

    def __init__(self, site_settings=None):
        self.site_settings = site_settings

    def __getattr__(self, attr):
        if attr in self.site_settings:
            return self.site_settings.get(attr)
        return super().__getattr__(attr)


cmsplus_settings = CmsPlusSettings(getattr(settings, 'CMSPLUS', {}))
