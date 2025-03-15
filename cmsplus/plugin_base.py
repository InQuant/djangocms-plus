import logging

from djangocms_frontend.cms_plugins import CMSUIPlugin
from djangocms_frontend.helpers import insert_fields

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.models import PlusItem
from cmsplus.forms import PlusPluginForm

logger = logging.getLogger('cmsplus')


class PlusPlugin(CMSUIPlugin):
    footnote_html = None
    form = PlusPluginForm
    model = PlusItem

    @classmethod
    def get_extra_css(cls, instance):
        return []


def get_fieldset_index(fieldsets, fields_key_to_search:str) -> int:
    """ returns the index of fieldset, where fields contains given key.

    e.g fieldsets:

    [
        (None, {'fields': [('container_type', 'plugin_title'), ('size_x', 'size_y')]}),
        ('Erweiterte Einstellungen', 'fields': ['tag_type', 'attributes'], })
    ]
    """
    return next((i for i, (_, value) in enumerate(fieldsets) if fields_key_to_search in value.get(
        'fields', [])), None)


class StylePluginMixin:
    """
    Mixin for PlusPluginBase class to provide extra css styles and classes.

    Extends get_identifier, get_css_classes, get_extra_css
    """
    footnote_html = None

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if instance.glossary.get('extra_css'):
            instance.add_classes(f'c-extra-{instance.id}')
        if instance.glossary.get('extra_style'):
            instance.add_classes(instance.glossary.get('extra_style').split())
        return context

    def get_fieldsets(self, request, obj=None):
        """Extend the fieldset of the plugin form.
        """
        fieldsets = super().get_fieldsets(request, obj)
        return insert_fields(
            fieldsets,
            (
                "extra_style",
                "extra_css",
            ),
            block=get_fieldset_index(fieldsets, 'attributes'),
        )

    def get_render_template(self, context, instance, placeholder):
        """ try to eval a template based on dirname of render_template and given
        extra_style name, e.g.: 'phoenix/plugins/c-category-tile.html'
        """
        if not getattr(self, 'render_template', None):
            return super().get_render_template(context, instance, placeholder)

        if not instance.glossary.get('extra_style'):
            return self.render_template

        style_template = getattr(
            cps, 'EXTRA_STYLE_TEMPLATES', {}).get(instance.glossary.get('extra_style'))
        if not style_template:
            return self.render_template

        return style_template

    @classmethod
    def get_glossary(cls, instance):
        return cls.form(data=instance.glossary).deserialize()

    @classmethod
    def get_extra_css(cls, instance):
        """
        gets the extra (device specific) css styles

        extra_css is stored device specific in config like this:
        extra_css : {
            'margin-bottom': '7rem',
            'margin-bottom:md': '13rem',
            'margin-bottom:xl': '30rem',
            'color': 'red',
            'color:md': 'blue',
        }

        returns from example:
            [
                'default', [
                    ('margin-bottom', '7rem'),
                    ('color', 'red'),
                ],
                '@media (min-width: 768px)', [
                    ('margin-bottom', '13rem'),
                    ('color', 'blue'),
                ],
                '@media (min-width: 768px)', [
                    ('margin-bottom', '30rem'),
                ],
            ]
        """

        def _get_media_and_css_key(key):
            """
            from e.g: margin-bottom:md ->  returns '@media (min-width: 768px)', margin-bottom
            """
            try:
                # k e.g. md:margin-bottom
                css_key, dev = key.split(':')
                media = '@media (min-width: %spx)' % cps.DEVICE_MIN_WIDTH_MAP.get(dev, 'xs')
            except ValueError:
                css_key = key
                media = 'default'
            return media, css_key

        css = {}
        extra_css = instance.glossary.get('extra_css')

        try:
            for key, val in extra_css.items():
                media, css_key = _get_media_and_css_key(key)
                if media in css:
                    _list = css[media]
                    _list.append((css_key, val))
                    css[media] = _list
                else:
                    css[media] = [(css_key, val), ]
        except AttributeError as e:
            logger.error(f'Error parsing extra_css for plugin {instance.id}')
            logger.exception(e)

        return css
