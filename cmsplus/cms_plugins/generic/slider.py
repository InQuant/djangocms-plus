import json

from django import forms
from django.utils.translation import gettext_lazy as _

from cmsplus.app_settings import cmsplus_settings
from cmsplus.forms import PlusPluginFormBase, AbstractLinkForm, get_style_form_fields
from cmsplus.models import PlusLinkedItem
from cmsplus.plugin_base import StylePluginMixin, LinkPluginMixin, PlusPlugin


def get_visible_slides_fields():
    n_choices = [(n, '%d slides' % n) for n in range(1, 16)]
    fields = []
    for dev in reversed(cmsplus_settings.DEVICES):
        if dev == 'xxl':
            initial = '3'
            required = True
            choices = n_choices
        else:
            initial = '1' if dev == 'sm' else ''
            required = False
            choices = [('', 'inherit'), ] + n_choices
        label = _('Num %s' % dev)

        field = forms.ChoiceField(label=label, required=required, choices=choices, initial=initial)
        fields.append(field)
    return fields


class SliderForm(PlusPluginFormBase):

    n_slides_xxl, n_slides_xl, n_slides_lg, n_slides_md, n_slides_sm, n_slides_xs = get_visible_slides_fields()

    TYPE_CHOICES = (
        ('carousel', 'Carousel'),
        ('slider', 'Slider'),
    )
    type = forms.ChoiceField(
        label=_('Slider type'),
        initial='carousel',
        choices=TYPE_CHOICES,
        help_text=_('slider: rewinds slider to the start/end, carousel: circles.'),
    )

    show_arrows = forms.BooleanField(
        label=_('Show Arrows'),
        initial=True,
        required=False,
        help_text=_('Show Slider Control Arrows?'),
    )

    gap = forms.IntegerField(
        label=_('Gap'),
        initial=10,
        help_text=_('Gap (px - default: 10) between slides.')
    )

    autoplay = forms.IntegerField(
        label=_('Autoplay'),
        initial=0,
        required=False,
        help_text=_('Duration (msec - default: 0) for infinite autoplay of slides (0 -> No autoplay.'),
    )

    animation_duration = forms.IntegerField(
        label=_('Animation Duration'),
        initial=400,
        required=False,
        help_text=_('Animation duration (msec - default: 400) - time between start and end of a slide change.'),
    )

    TIMING_FUNC_CHOICES = (
        ('cubic-bezier(0.165, 0.840, 0.440, 1.000)', 'Default'),
        ('linear', 'Linear'),
        ('ease', 'Ease'),
        ('ease-in', 'Ease In'),
        ('ease-out', 'Ease Out'),
        ('ease-in-out', 'Ease In/Out'),
        ('Bounce', 'Bounce'),
    )
    animation_timing_func = forms.ChoiceField(
        label=_('Animation Timing'),
        initial='cubic-bezier(0.165, 0.840, 0.440, 1.000)',
        choices=TIMING_FUNC_CHOICES,
        help_text=_('Animation timing, e.g.: Start: quick - end: slow.'),
    )

    hoverpause = forms.BooleanField(
        label=_('Hoverpause'),
        initial=True,
        required=False,
        help_text=_('Stop autoplay on mouse over.'),
    )

    peek = forms.IntegerField(
        label=_('Peek'),
        initial=0,
        help_text=_('Preview width (px) of next and previous hided slides.'),
    )

    STYLE_CHOICES = 'SLIDER_STYLES'
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)

    def clean(self):
        super().clean()
        breakpoints = {}
        for dev in reversed(cmsplus_settings.DEVICES):
            key = 'n_slides_%s' % dev
            width = cmsplus_settings.DEVICE_MAX_WIDTH_MAP[dev]
            if self.cleaned_data.get(key):
                breakpoints[width] = {'perView': int(self.cleaned_data[key])}
        self.cleaned_data['breakpoints'] = breakpoints


class SliderPlugin(StylePluginMixin, PlusPlugin):
    name = "Slider"
    require_parent = False
    child_classes = ['SlidePlugin', ]
    allow_children = True
    alien_child_classes = False
    form = SliderForm
    render_template = 'cmsplus/generic/slider/slider.html'
    footnote_html = "Base for a slider component."

    fieldsets = [
        (None, {
            'fields': (
                ('n_slides_xxl', 'n_slides_xl', 'n_slides_lg', 'n_slides_md', 'n_slides_sm', 'n_slides_xs',),
                ('gap', 'peek',),
                ('type', 'autoplay'),
                ('show_arrows', 'hoverpause',),
                ('animation_duration', 'animation_timing_func'),
            ),
            'description': _('Number of visible slides for the different device sizes:'),
        }),
    ]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        instance.add_classes('glide', 'glide-swipeable')
        context['slider_config'] = json.dumps(instance.glossary)
        return context

    @classmethod
    def sanitize_model(cls, obj):
        breakpoints = {}
        for dev in reversed(cmsplus_settings.DEVICES):
            key = 'n_slides_%s' % dev
            width = cmsplus_settings.DEVICE_MAX_WIDTH_MAP[dev]
            if obj.glossary.get(key):
                breakpoints[width] = {'perView': int(obj.glossary[key])}
        obj.config['breakpoints'] = breakpoints
        return True

class SlideForm(AbstractLinkForm):
    require_link = False

    STYLE_CHOICES = 'SLIDE_STYLES'
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)


class SlidePluginModel(PlusLinkedItem):
    class Meta:
        proxy = True


class SlidePlugin(StylePluginMixin, LinkPluginMixin, PlusPlugin):
    name = "Slide"
    parent_classes = ['SliderPlugin', ]
    allow_children = True
    alien_child_classes = True
    render_template = 'cmsplus/generic/slider/slider_child.html'
    model = SlidePluginModel

    form = SlideForm

    class Media:
        js = [
            'admin/js/jquery.init.js',
        ]

    fieldsets = [
        (None, {
            'fields': (
            ),
            'description': _('Nothing to input here:'),
        }),
    ]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        instance.add_classes('glide', 'glide-swipeable')
        context['slider_config'] = json.dumps(instance.glossary)
        return context