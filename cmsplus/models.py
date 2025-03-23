from django.utils.functional import cached_property
from djangocms_frontend.models import FrontendUIItem
from djangocms_frontend.contrib.link.models import GetLinkMixin

class PlusItemMixin:
    def __str__(self):
        return self.get_short_description()

    def get_short_description(self):
        return self.title or self._meta.verbose_name
    
    def __getattr__(self, item):
        """Makes properties of plugin config available as plugin properties."""
        if item[0] != "_" and item in self.glossary:  # Avoid infinite recursion trying to get .config from db
            return self.glossary.get(item)
        return super().__getattribute__(item)

    def save(self, *args, **kwargs):
        if getattr(self.plugin_class, 'sanitize_model', None):
            self.plugin_class.sanitize_model(self)
        self._glossary = None
        super().save(*args, **kwargs)

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
    
class PlusItem(PlusItemMixin, FrontendUIItem):
    class Meta:
        proxy = True
        verbose_name = "PUI item"

class PlusLinkedItem(GetLinkMixin, PlusItem):
    class Meta:
        proxy = True
        verbose_name = "PUI item"
