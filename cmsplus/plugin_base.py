import logging

from django.utils.translation import gettext_lazy as _
from djangocms_frontend.cms_plugins import CMSUIPlugin
from djangocms_frontend.helpers import insert_fields

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.models import PlusItem, PlusLinkedItem
from cmsplus.forms import PlusPluginForm

logger = logging.getLogger('cmsplus')


class PlusPlugin(CMSUIPlugin):
    footnote_html = None
    form = PlusPluginForm
    model = PlusItem

    @classmethod
    def get_glossary(cls, instance):
        return cls.form(data=instance.config).deserialize()

    @classmethod
    def get_extra_css(cls, instance):
        return []

    @classmethod
    def sanitize_model(cls, instance):
        return True


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

    block_attr = {
        "description": _(
            "Advanced settings lets you add html attributes to render this element. Use them wisely and rarely."
        ),
        "classes": (
            "collapse",
            "attributes",
        ),
    }

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        attribute_block_index = get_fieldset_index(fieldsets, 'attributes')

        if attribute_block_index:
            # if attribute block found because AttributeMixin is present
            return insert_fields(
                fieldsets,
                (
                    "extra_style",
                    "extra_css",
                ),
                block=attribute_block_index,
            )

        # otherwise build your own Advanced Settings block
        meta = self.form._meta
        fields = ["tag_type"] if "tag_type" in getattr(meta, "untangled_fields", ()) else []
        if "plugin_title" in self.form.declared_fields.keys():
            fields.append("plugin_title")
        fields.append("attributes")
        fields.append("extra_style")
        fields.append("extra_css")
        return insert_fields(
            fieldsets,
            fields,
            blockname=_("Advanced settings"),
            blockattrs=self.block_attr,
            position=-1,  # Always last
        )


    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if instance.glossary.get('extra_css'):
            instance.add_classes(f'c-extra-{instance.id}')
        if instance.glossary.get('extra_style'):
            instance.add_classes(instance.glossary.get('extra_style').split())
        if instance.glossary.get('plugin_title') and instance.plugin_title.get('show'):
            instance.add_attribute('title', instance.plugin_title.get('title'))
        return context

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
        return cls.form(data=instance.config).deserialize()

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


class LinkPluginMixin:
    model = PlusLinkedItem
    link_fieldset_position = -1
    link_fields = ("link", "target")

    def get_form(self, request, obj=None, change=False, **kwargs):
        """The link form needs the request object to check permissions"""
        form = super().get_form(request, obj, change, **kwargs)
        form.request = request
        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if self.link_fieldset_position is not None:
            fieldsets = insert_fields(
                fieldsets,
                self.link_fields,
                blockname=_("Link settings"),
                position=self.link_fieldset_position,
            )
        return fieldsets

    def render(self, context, instance, placeholder):
        context['plus_item_link'] = instance.get_link()
        return super().render(context, instance, placeholder)