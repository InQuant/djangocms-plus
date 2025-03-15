from django import forms
from cmsplus.app_settings import cmsplus_settings as cps

def get_img_dev_width_fields(initials=None):
    initials = {} if not initials else initials
    fields = []
    for dev in cps.DEVICES:

        # e.g. label = 'phone width'
        label = '%s Width' % cps.DEVICE_MAP[dev].title()

        if dev == 'xs':
            field = forms.ChoiceField(
                label=label,
                choices=cps.IMG_DEV_WIDTH_CHOICES,
                initial=initials.get('xs', '1/2'))
        else:
            field = forms.ChoiceField(
                label=label,
                required=False,
                choices=[('', 'inherit'), ] + list(cps.IMG_DEV_WIDTH_CHOICES),
                initial=initials.get(dev, ''))

        field_name = 'img_dev_width_%s' % dev
        fields.append((field_name, field))
    return fields

def get_img_dev_width_field_names():
    return [n[0] for n in get_img_dev_width_fields()]

def get_img_dev_width_mapping(column_width):
    """
    returns a img_dev_width mapping for a given column_dev_width, e.g.
        - col-md-12 -->: 1
        - col-lg-6 -->: 1/2
    """
    wmap = {
        '1': '1/6', '2': '1/5', '3': '1/4', '4': '1/3', '5': '1/2', '6': '1/2',
        '7': '2/3', '8': '2/3', '9': '3/4', '10': '1', '11': '1', '12': '1',
    }
    k = column_width.rsplit('-', 1)[1]
    return wmap.get(k)

