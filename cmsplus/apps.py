import logging
import operator

from django.apps import AppConfig
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


def get_toolbar_plugin_struct(plugins, slot=None, page=None):
    """
       Return the list of plugins to render in the toolbar.
       The dictionary contains the label, the classname and the module for the
       plugin.
       Names and modules can be defined on a per-placeholder basis using
       'plugin_modules' and 'plugin_labels' attributes in CMS_PLACEHOLDER_CONF

       :param plugins: list of plugins
       :param slot: placeholder slot name
       :param page: the page
       :return: list of dictionaries
    """
    from cms.utils.placeholder import get_placeholder_conf
    template = None

    if page:
        template = page.template

    modules = get_placeholder_conf("plugin_modules", slot, template, default={})
    names = get_placeholder_conf("plugin_labels", slot, template, default={})

    main_list = []

    # plugin.value points to the class name of the plugin
    # It's added on registration. TIL.
    for plugin in plugins:
        footnote_html = getattr(plugin, 'footnote_html', None)
        if footnote_html:
            footnote_html = strip_tags(footnote_html)

        main_list.append({'value': plugin.value,
                          'name': names.get(plugin.value, plugin.name),
                          'footnote': footnote_html,
                          'module': modules.get(plugin.value, plugin.module)})
    return sorted(main_list, key=operator.itemgetter("module"))


def unregister_plugins():
    from cms.plugin_pool import plugin_pool
    from djangocms_link.cms_plugins import LinkPlugin
    logger.info('** unregister djangocms_link.LinkPlugin')
    plugin_pool.unregister_plugin(LinkPlugin)

def register_plus_plugins():
    logger.info('** register plus plugins')
    from importlib import import_module
    from cms.plugin_pool import plugin_pool
    from cmsplus.app_settings import cmsplus_settings as cps

    # register all plugins configured cmsplus app_settings
    for plugin in cps.PLUGINS:
        mod_name, cls_name = plugin.rsplit('.', 1)
        mod = import_module(mod_name)
        cls = getattr(mod, cls_name)
        plugin_pool.register_plugin(cls)

class DjangoCmsPlusConfig(AppConfig):
    name = 'cmsplus'
    verbose_name = _('DjangoCMS Plus')

    def ready(self):
        super().ready()

        unregister_plugins()
        register_plus_plugins()

        # monkey patch 'cms.utils.placeholder.get_toolbar_plugin_struct'
        import cms.utils.placeholder

        #cms.utils.placeholder.get_toolbar_plugin_struct = get_toolbar_plugin_struct
        logger.info('** Monkey Patched: "cms.utils.placeholder.get_toolbar_plugin_struct"')
