from django import template
from django.conf import settings

register = template.Library()

# settings value
@register.simple_tag
def settings_value(name):
    # dont serve arbitrary settings
    whitelist = ('SITE_NAME', 'SITE_URL', 'SITE_MY_NAME', 'SITE_MY_URL', 
        'BG_INFO_MAIL', 
        'EMAIL_HOST_USER', 'LINK_REL_STATUTEN', 'LINK_REL_REGLEMENT', 
        'MAP_CENTER_LAT', 'MAP_CENTER_LONG', 'MAP_CENTER_ZOOM'
    )
    if name in whitelist:
        return getattr(settings, name, "")
    return '[not permitted]'
 
@register.simple_tag
def boehnli_progress(participants, slots):
    title = "%d von %d gebucht" % (len(participants), len(slots))
    text = ""
    for i in slots:
        if i < len(participants):
            text += '<img class="jobstatus" src="/static/img/erbse_voll.png" title="%s"/> ' % title
        else:
            text += '<img class="jobstatus" src="/static/img/erbse_leer.png" title="%s"/> ' % title
    return text + '&nbsp;' + title


@register.simple_tag
def ga_tracking():
    if settings.GA_TRACKING_CODE:
        code = """<script>
                  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
                  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
                  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
                  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

                  ga('create', '[[code]]', 'auto');
                  ga('send', 'pageview');

                  </script>"""
        return code.replace('[[code]]', settings.GA_TRACKING_CODE)          
    else:
        return '<!-- no tracking code set -->'
