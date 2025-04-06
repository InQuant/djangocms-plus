from django import forms
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings as cps
from cmsplus.forms import PlusStylePluginFormBase
from cmsplus.plugin_base import PlusStylePlugin
from cmsplus.utils import insert_fieldset


# MultiColTextPlugin
# ------------------
#
class MultiColTextForm(PlusStylePluginFormBase):
    STYLE_CHOICES = 'MOD_COL_STYLES'

    @staticmethod
    def get_col_choice_fields():
        def _get_col_choice_field(dev):
            if dev == 'xs':
                choices = [('', '1 (default)'), ]
            else:
                choices = [('', 'inherit'), ]
            choices.extend(list(cps.TX_COL_CHOICES))

            field_name = 'col_%s' % dev
            field = forms.ChoiceField(
                label=u'%s No. of Cols' % cps.DEVICE_MAP[dev], required=False, choices=choices, initial='')
            return field_name, field

        fields = []
        for dev in cps.DEVICES:
            fields.append(_get_col_choice_field(dev))
        return fields

    @classmethod
    def extend_col_fields(cls):
        cls.declared_fields.update(cls.get_col_choice_fields())

MultiColTextForm.extend_col_fields()


class MultiColumnTextPlugin(PlusStylePlugin):
    footnote_html = """
    renders a wrapper for a multi column text.
    """
    name = 'MultiColumnText'
    form = MultiColTextForm
    render_template = "cmsplus/generic/multi-col-text.html"
    allow_children = True

    mct_fieldset = (None, {
        'fields': (
            (*[name for name, _ in form.get_col_choice_fields()],),
        ),
        'description': _('Number of text cols for the different device sizes:'),
    })

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        keys_to_remove = self.form.declared_fields.keys()

        return insert_fieldset(fieldsets, self.mct_fieldset, 0, keys_to_remove)

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        for dev in cps.DEVICES:
            v = getattr(instance, f'col_{dev}')
            if v: instance.add_classes(f'c-text-col-{v}')
        return context
