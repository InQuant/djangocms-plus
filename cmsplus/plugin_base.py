import logging

from cms.plugin_base import CMSPluginBase
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.models import PlusItem
from cmsplus.forms import PlusPluginFormBase, PlusStylePluginFormBase
from cmsplus.utils import insert_fieldset

from markdown import markdown

logger = logging.getLogger('cmsplus')


class PlusPlugin(CMSPluginBase):
    footnote_html = None
    form = PlusPluginFormBase
    model = PlusItem
    render_template = "cmsplus/container.html"
    change_form_template = "cmsplus/admin/plugin/change_form.html"
    tag_type = 'div'

    extra_settings_fields = ['plugin_title', 'attributes']

    def save_form(self, request, form, change):
        """
        Set CMSPlugin required attributes
        """
        obj = form.save(commit=False)
        for field, value in self._cms_initial_attributes.items():
            # Set the initial attribute hooks (if any)
            setattr(obj, field, value)
        return obj

    def get_fieldsets(self, request, obj=None):
        declared_fields = list(self.form.declared_fields.keys())

        # field for category Extra Settings
        extra_fields = self.extra_settings_fields

        # all others below None
        main_fields = [f for f in declared_fields if f not in extra_fields]

        fieldsets = []
        if main_fields:
            fieldsets.append((None, {'fields': main_fields}))
        if extra_fields:
            fieldsets.append((
                "Extra Settings",
                {
                    'classes': ['collapse',],
                    'fields': extra_fields,
                }
            ))
        return fieldsets

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        if instance.glossary.get('plugin_title') and instance.plugin_title.get('show'):
            instance.add_attribute('title', instance.plugin_title.get('title'))

        if instance.glossary.get('attributes'):
            for key, val in instance.glossary.get('attributes').items():
                instance.add_attribute(key, val)
        return context

    @classmethod
    def get_glossary(cls, instance):
        return cls.form(data=instance.config).deserialize_data()

    @classmethod
    def get_tag_type(cls, instance):
        """
        Return the tag_type used to render this plugin.
        """
        return instance.glossary.get('tag_type', getattr(cls, 'tag_type', cls.tag_type))

    @classmethod
    def get_extra_css(cls, instance):
        return []

    @classmethod
    def sanitize_model(cls, instance):
        """
        This method is called, before the model is saved to the database. It can be overloaded to sanitize the current
        (_json) data dict of the instance.
        """
        if instance.config is None: instance.config = {}

    @classmethod
    def get_identifier(cls, instance):
        """
        Hook to return a description for the current model.

        If there is a choice field 'extra_styles' in the plugins form: try to get plugins identifier via the current
        selected extra style name.
        """
        return ""

    @classmethod
    def footnote_as_html(cls):
        if getattr(cls, 'footnote_html', ''):
            return mark_safe(markdown(cls.footnote_html))
        return 'foo'



def get_fieldset_index(fieldsets, fields_key_to_search:str) -> int:
    """ returns the index of fieldset, where fields contains given key.

    e.g fieldsets:

    [
        (None, {'fields': [('container_type', 'plugin_title'), ('size_x', 'size_y')]}),
        ('Extra Settings', 'fields': ['tag_type', 'attributes'], })
    ]
    """
    return next((i for i, (_, value) in enumerate(fieldsets) if fields_key_to_search in value.get(
        'fields', [])), None)

class PlusStylePlugin(PlusPlugin):
    """
    Extension for PlusPluginBase class to provide extra css styles and classes.

    Extends get_identifier, get_css_classes, get_extra_css
    """
    footnote_html = None
    form = PlusStylePluginFormBase

    extra_settings_fields = PlusPlugin.extra_settings_fields + ['extra_style', 'extra_css']

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        if instance.glossary.get('extra_style'):
            instance.add_classes(instance.glossary.get('extra_style').split())

        if instance.glossary.get('extra_css'):
            instance.add_classes(f'c-extra-{instance.id}')

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
        return cls.form(data=instance.config).deserialize_data()

    @classmethod
    def get_extra_css(cls, instance):
        """
        gets the extra (device specific) css styles

        extra_css is stored device specific in _json like this:
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
    link_fieldset_index = 1

    def get_form(self, request, obj=None, change=False, **kwargs):
        """The link form needs the request object to check permissions"""
        form = super().get_form(request, obj, change, **kwargs)
        form.request = request
        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        name = 'Link'
        css = 'collapse'
        if self.__class__.__name__ == 'LinkPlugin':
            name = None
            css = ""

        link_fieldset = (name, {
            'classes': (css,),
            'fields': ('link', 'target', 'link_attributes'),
        })
        return insert_fieldset(fieldsets, link_fieldset, self.link_fieldset_index, ['link', 'target', 'link_attributes'])

    def render(self, context, instance, placeholder):
        if "request" in context:
            instance._cms_page = getattr(context["request"], "current_page", None)
        context['link'] = instance.get_link(
            #instance.link, getattr(get_current_site(context["request"]), "id", None)
        )
        return super().render(context, instance, placeholder)
