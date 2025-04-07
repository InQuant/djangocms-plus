from uuid import uuid4
from cms.models import CMSPlugin
from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.html import conditional_escape, mark_safe
from django.utils.translation import gettext_lazy as _

from djangocms_link.helpers import get_link

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.utils import import_class_from_str

class PlusItemMixin:

    def __init__(self, *args, **kwargs):
        self._additional_classes = []
        super().__init__(*args, **kwargs)

    def __str__(self):
        return str(self.get_short_description())

    def get_short_description(self):
        return self.title or self.plugin_class.get_identifier(self) or self._meta.verbose_name
    
    def __getattr__(self, item):
        """Makes properties of plugin glossary available as plugin properties."""
        if item[0] != "_" and item in self.glossary:  # Avoid infinite recursion trying to get .config from db
            return self.glossary.get(item)
        return super().__getattribute__(item)

    def save(self, *args, **kwargs):
        if getattr(self.plugin_class, 'sanitize_model', None):
            self.plugin_class.sanitize_model(self)
        self._glossary = None
        super().save(*args, **kwargs)

    def add_classes(self, *args):
        for arg in args:
            if arg:
                self._additional_classes += arg.split() if isinstance(arg, str) else arg

    def add_attribute(self, attr, value=None):
        attrs = self.glossary.get("attributes", {})
        if attr == "style" and attr in attrs:
            value += attrs[attr]
        attrs.update({attr: value})
        self.glossary["attributes"] = attrs

    def get_attributes(self):
        attributes = self.glossary.get("attributes", {})
        classes = set(attributes.get("class", "").split())  # classes added in attriutes
        classes.update(self._additional_classes)  # add additional classes
        classes = (f'class="{conditional_escape(" ".join(classes))}"') if classes else ""  # to string
        parts = (
            f'{item}="{conditional_escape(value)}"' if value else f"{item}"
            for item, value in attributes.items()
            if item != "class"
        )
        attributes_string = (classes + " ".join(parts)).strip()
        return mark_safe(" " + attributes_string) if attributes_string else ""

    @property
    def glossary(self):
        if not getattr(self, '_glossary', None):
            self._glossary = self.plugin_class.get_glossary(self)
        return self._glossary

    @property
    def errors(self):
        glossary = self.plugin_class.get_glossary(self)
        form = self.plugin_class.form(data=glossary)
        return form.errors

    @property
    def tag_type(self):
        return self.plugin_class.get_tag_type(self)

    @property
    def title(self):
        try:
            return self.glossary.get("plugin_title", {}).get("title", "")
        except:
            return None

    @cached_property
    def plugin_class(self):
        return self.get_plugin_class()

    @property
    def extra_css(self):
        """
        returns e.g: [
            ('default', 'margin-bottom:2rem;border:2px solid black'),
            ('@media (min-width: 768px)', 'margin-bottom:3rem)'
        ]
        """
        css = []
        for media, css_lines in self.plugin_class.get_extra_css(self).items():
            _css = ';'.join(['%s:%s' % (k, v) for k, v in css_lines])
            css.append((media, _css))
        return css



class LinkItemMixin:

    def get_link(self, site_id=None):
        return get_link(self.link, site_id)


class PlusItem(PlusItemMixin, LinkItemMixin, CMSPlugin):
    _json = models.JSONField(encoder=import_class_from_str(cps.JSON_ENCODER_CLASS))
    class Meta:
        verbose_name = "Plus item"

    @property
    def config(self):
        """ raw glossary data """
        return self._json

    @config.setter
    def config(self, value: dict):  # noqa E999
        self._json = value
