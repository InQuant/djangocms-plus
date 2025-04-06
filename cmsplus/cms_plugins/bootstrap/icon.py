import json
import os

from django import forms
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.forms.renderers import get_default_renderer
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.forms import LinkFormMixin
from cmsplus.plugin_base import LinkPluginMixin
from cmsplus.cms_plugins.bootstrap.base import BootstrapFormBase, BootstrapPluginBase


class IconFieldWidget(forms.Widget):
    template_name = "cmsplus/admin/widgets/icon.html"
    icons = []

    def __init__(self, attrs=None):
        super().__init__(attrs)

        # add fontawesome
        if cps.ICONS_FONTAWESOME and cps.ICONS_FONTAWESOME_SHOW:
            self.icons += self.get_fontawesome_icons

        # add bootstrap
        if cps.ICONS_BOOTSTRAP and cps.ICONS_BOOTSTRAP_SHOW:
            self.icons += self.get_bootstrap_icons

        # add icons
        for font in getattr(cps, 'ICONS_FONTELLO', []):
            self.icons += self.get_fontello(font)

    def render(self, name, value, add_to_class=None, attrs=None, renderer=None):
        if renderer is None:
            renderer = get_default_renderer()

        icons = IconFieldWidget.icons

        # add "no-icon" if not required
        if not attrs.get('required'):
            if not any(f['font_class_name'] == 'cmsplus-icon-none' for f in icons):
                icons.insert(0, {
                    'name': _('No icon'),
                    'label': _('No icon'),
                    'font_class_name': 'cmsplus-icon-none'
                })

        context = self.get_context(name, value, attrs)
        context['widget']['icons'] = IconFieldWidget.icons
        context['widget']['value'] = value
        context['widget']['name'] = name
        context['widget']['attrs'] = attrs
        context['widget']['add_to_class'] = add_to_class
        return mark_safe(renderer.render(self.template_name, context))

    @cached_property
    def get_bootstrap_icons(self):
        icons = []
        path = finders.find(cps.ICONS_BOOTSTRAP['meta'])
        if not path or not os.path.exists(path):
            raise ImproperlyConfigured('ICONS_FONTAWESOME: meta path is not existing (%s)' % path)

        with open(path, 'rb') as f:
            raw_data = f.read()
        try:
            data = json.loads(raw_data)
        except TypeError:
            # Python 3.5 compatibility
            data = json.loads(raw_data.decode('utf-8'))

        for key, value in data.items():
            icons.append({
                'name': key,
                'label': key,
                'font_class_name': f'bi bi-{key}',
            })
        return icons

    @cached_property
    def get_fontawesome_icons(self):
        icons = []
        # list of dicts:
        # { 'name': '',
        #   'label': '',
        #   'font_class_name': '', }

        path = finders.find(cps.ICONS_FONTAWESOME['meta'])
        if not path or not os.path.exists(path):
            raise ImproperlyConfigured('ICONS_FONTAWESOME: meta path is not existing (%s)' % path)

        with open(path, 'rb') as f:
            raw_data = f.read()
        try:
            data = json.loads(raw_data)
        except TypeError:
            # Python 3.5 compatibility
            data = json.loads(raw_data.decode('utf-8'))

        for key, value in data.items():
            # check styles ['brands', 'solid', 'regular']
            for style in value.get('styles'):
                if style == "solid":
                    font_class_name = "fas fa-%s" % key
                elif style == "brands":
                    font_class_name = "fab fa-%s" % key
                elif style == "regular":
                    font_class_name = "far fa-%s" % key
                else:
                    raise ValueError("%s style not defined" % style)

                icons.append({
                    'name': key,
                    'label': value.get('label'),
                    'font_class_name': font_class_name,
                })
        return icons

    @staticmethod
    def get_fontello(attrs):
        icons = []
        path = finders.find(attrs.get('meta'))
        if not path or not os.path.exists(path):
            raise ImproperlyConfigured('CMSPLUS SETTINGS - ICONS: path is not existing (%s)' % path)

        with open(path, 'rb') as f:
            raw_data = f.read()
        try:
            data = json.loads(raw_data)
        except TypeError:
            # Python 3.5 compatibility
            data = json.loads(raw_data.decode('utf-8'))

        prefix = data.get('css_prefix_text', 'icon-')
        for glyph in data.get('glyphs', []):
            if not glyph.get('css'):
                continue

            icons.append({
                'name': glyph.get('css'),
                'label': glyph.get('css'),
                'font_class_name': "%s%s" % (prefix, glyph.get('css')),
            })
        return icons


class IconField(forms.CharField):
    widget = IconFieldWidget


class IconFormMixin(forms.Form):
    icon = IconField(required=True)


class IconForm(LinkFormMixin, IconFormMixin, BootstrapFormBase):
    require_link = False
    STYLE_CHOICES = 'MOD_ICON_STYLES'


def get_icon_style_paths():
    paths = []
    if cps.ICONS_FONTAWESOME and cps.ICONS_FONTAWESOME_SHOW:
        paths.append(cps.ICONS_FONTAWESOME.get('css'))

    if cps.ICONS_BOOTSTRAP and cps.ICONS_BOOTSTRAP_SHOW:
        paths.append(cps.ICONS_BOOTSTRAP.get('css'))

    for font in getattr(cps, 'ICONS_FONTELLO', []):
        if font.get('css'):
            paths.append(font.get('css'))
    return paths


class IconPluginMixin:
    class Media:
        css = {'all': ['cmsplus/admin/icon_plugin/css/icon_plugin.css'] + get_icon_style_paths()}
        js = ['cmsplus/admin/icon_plugin/js/icon_plugin.js']

class IconPlugin(LinkPluginMixin, IconPluginMixin, BootstrapPluginBase):
    footnote_html = """
    Choose icon from font defined in the settings
    """
    name = 'Icon'
    form = IconForm
    render_template = "cmsplus/bootstrap/icon.html"
    allow_children = False
    text_enabled = True
    tag_type = 'i'

    @classmethod
    def get_identifier(cls, instance):
        return str(instance.icon)

    def render(self, context, instance, placeholder):
        if instance.icon:
            instance.add_classes(instance.icon)
        return super().render(context, instance, placeholder)
