# DjangoCMS Plus

An addon for Django CMS > 4 which offers a set of generic and bootstrap 5 plugins with use of pure JS, easy to adapt.
It was inspired from `djangocms-frontend` but with much simpler and cleaner code and handling e.g. `entangled` form mess.
## Features

- All plugin data stored as JSON, no need for migrations if plugin changes
- Easy reuse of plugins in templates with `plugin` tag
- Provides a Slider plugin which uses `glide.js`
- Works perfectly with `djangocms-content-transfer` to transfer Page Structures between systems, e.g. between dev and productive instances.
## Installation

1. `pip install git+https://github.com/InQuant/djangocms-plus.git`
2. npm install

```json
    "dependencies": {
        "@glidejs/glide": "^3.4",
        "bootstrap": "^5",
        "bootstrap-icons": "",
        "select2": "^4.1",
    },
```

3. add `cmsplus` to `INSTALLED_APPS`
4. optional add CMSPLUS section to your project settings.py and adapt icon locations.

```python
    CMSPLUS = {
        'ICONS_BOOTSTRAP': {
            'meta': 'node_modules/bootstrap-icons/font/bootstrap-icons.json',
            'css': 'node_modules/bootstrap-icons/font/bootstrap-icons.css',
        }
    }
```
