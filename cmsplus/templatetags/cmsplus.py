import typing
from classytags.arguments import Argument, MultiKeywordArgument
from classytags.core import Options, Tag
from classytags.helpers import AsTag
from django import template
from django import template
from django.conf import settings
from django.db import models
from django.utils.html import conditional_escape, mark_safe

from cmsplus.models import PlusItem

register = template.Library()

@register.simple_tag
def get_attributes(attribute_field, *add_classes):
    """Joins a list of classes with an attributes field and returns all html attributes"""
    additional_classes = set()
    for classes in add_classes:
        if classes:
            additional_classes.update(classes.split() if isinstance(classes, str) else classes)
    attrs = []
    if attribute_field:
        for key, val in attribute_field.items():
            if key.lower() == "class":
                val = " ".join(additional_classes.union(set(val.split())))
            if val:
                attrs.append(f'{key}="{conditional_escape(val)}"')
            else:
                attrs.append(f"{key}")
    if additional_classes and (not attribute_field or "class" not in attribute_field):
        attrs.append(f'class="{conditional_escape(" ".join(additional_classes))}"')
    return mark_safe(" ".join(attrs))


@register.tag
class SlotTag(Tag):
    name = "slot"
    options = Options(
        Argument("slot_name", required=True),
        blocks=[("endslot", "nodelist")],
    )

    def render_tag(self, context, slot_name, nodelist):
        return ""


class DummyPlugin:
    def __init__(self, nodelist, plugin_type, slot_name: typing.Optional[str] = None) -> "DummyPlugin":
        self.nodelist = nodelist
        self.plugin_type = (f"{plugin_type}{slot_name.capitalize()}Plugin") if slot_name else "DummyPlugin"
        if slot_name is None:
            self.parse_slots(nodelist, plugin_type)
        super().__init__()

    def parse_slots(self, nodelist, plugin_type):
        self.slots = [self]
        for node in nodelist:
            if isinstance(node, SlotTag):
                self.slots.append(DummyPlugin(node.nodelist, plugin_type, node.kwargs.get("slot_name")))

    def get_instances(self):
        return self.slots


class Plugin(AsTag):
    """ Taken and adapted from djangocms-frontend
    """
    name = "plugin"
    options = Options(
        Argument("name", required=True),
        MultiKeywordArgument("kwargs", required=False),
        "as",
        Argument("varname", resolve=False, required=False),
        blocks=[("endplugin", "nodelist")],
    )

    def message(self, message):
        import warnings

        warnings.warn(message, stacklevel=5)
        return f"<!-- {message} -->" if settings.DEBUG else ""

    def get_value(self, context, name, kwargs, nodelist):
        from cmsplus.plugin_tag import plugin_tag_pool

        if name not in plugin_tag_pool:
            return self.message(
                f'To use "{name}" with the {{% plugin %}} template tag, add its plugin class to '
                f"the CMS_COMPONENT_PLUGINS setting"
            )
        context.push()
        plugin_class = plugin_tag_pool[name]["class"]

        # Create context
        if issubclass(plugin_class.model, PlusItem):
            instance = plugin_class.model(plugin_class=plugin_class, **kwargs)
        else:
            instance = plugin_class.model(**kwargs)

        context["instance"] = instance

        # Call render method of plugin
        context = plugin_class().render(context, instance, None)
        # Replace inner plugins with the nodelist, i.e. the content within the plugin tag
        instance.child_plugin_instances = DummyPlugin(
            nodelist, context["instance"].plugin_type
        ).get_instances()
        # ... and render
        result = plugin_tag_pool[name]["template"].render(context.flatten())
        context.pop()
        return result


register.tag(Plugin.name, Plugin)