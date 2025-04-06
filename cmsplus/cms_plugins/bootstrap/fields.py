from django import forms
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from cmsplus.app_settings import cmsplus_settings as cps

class ColorPickerWidget(forms.Widget):
    template_name = "cmsplus/admin/widgets/colorpicker.html"

    def __init__(self, choices=None, attrs=None):
        super().__init__(attrs)
        self.choices = choices or [
            ("primary", "Primary"),
            ("secondary", "Secondary"),
            ("success", "Success"),
            ("danger", "Danger"),
            ("warning", "Warning"),
            ("info", "Info"),
            ("light", "Light"),
            ("dark", "Dark"),
        ]

    def render(self, name, value, attrs=None, renderer=None):
        widget_id = attrs.get("id", f"color_{name}")
        color_objects = [
            {"value": val, "label": label, "css_class": f"bg-{val}", "is_empty": val == ""}
            for val, label in self.choices
        ]

        context = {
            "widget": {
                "name": name,
                "value": value,
                "attrs": attrs,
                "colors": color_objects,
                "id": widget_id,
            }
        }
        return mark_safe(render_to_string(self.template_name, context))


class BootstrapClassHelperWidgetBase(forms.TextInput):
    help_url = f'{cps.BOOTSTRAP_DOC_URL}/'
    help_url_display = 'Bootstrap Utilities'
    help_text = 'helping info'

    def __init__(self, attrs=None):
        # full-width for text-input
        base_attrs = {'class': 'form-control w-100'}
        if attrs:
            base_attrs.update(attrs)
        super().__init__(attrs=base_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # render normal text field
        field_html = super().render(name, value, attrs, renderer)

        # Helptext + Link
        help_html = format_html(
            (f'<small class="form-text text-muted">{self.help_text} - see <a href="{self.help_url}" target="_blank" '
             f'rel="noopener noreferrer">{self.help_url_display}</a>.</small>')
        )
        return mark_safe(f"{field_html}\n{help_html}")

class SpacingWidget(BootstrapClassHelperWidgetBase):
    help_url = f'{cps.BOOTSTRAP_DOC_URL}/utilities/spacing/'
    help_url_display = 'Bootstrap Spacing Utilities'

    spacer_range = f'[0 - {cps.SPACING_VALUE_LIMIT}]'
    help_text = f'Spacing classes, e.g. `px-3 px-lg-5`- possible values: {spacer_range}'

class RowColsWidget(BootstrapClassHelperWidgetBase):
    help_url = f'{cps.BOOTSTRAP_DOC_URL}/layout/grid/#row-columns'
    help_url_display = 'Bootstrap Row columns'
    help_text = f'Row column classes, e.g. `row-cols-2 row-cols-lg-4`'

class ColsWidget(BootstrapClassHelperWidgetBase):
    help_url = f'{cps.BOOTSTRAP_DOC_URL}/layout/columns/'
    help_url_display = 'Bootstrap Columns'
    help_text = f'Column classes, e.g. `col-6 col-lg-3`'
