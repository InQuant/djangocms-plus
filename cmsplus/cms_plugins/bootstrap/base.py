from cmsplus.forms import PlusStylePluginFormBase
from cmsplus.plugin_base import PlusStylePlugin

class BootstrapFormBase(PlusStylePluginFormBase):
    pass

class BootstrapPluginBase(PlusStylePlugin):
    module = 'Bootstrap'
    form = BootstrapFormBase
