from django import template
from django.conf import settings

register = template.Library()

# settings value
@register.simple_tag
def settings_value(name):
    if name in ('SITE_NAME', 'SITE_URL', ):
        return getattr(settings, name, "")
    return '[not permitted]'
 
