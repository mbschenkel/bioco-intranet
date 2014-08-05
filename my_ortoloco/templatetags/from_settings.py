# encoding: utf-8

from django import template
from django.conf import settings
import HTMLParser
from django.utils.html import strip_tags
 
register = template.Library()

# settings value
@register.simple_tag
def settings_value(name):
    # dont serve arbitrary settings
    whitelist = ('SITE_NAME', 'SITE_URL', 'SITE_MY_NAME', 'SITE_MY_URL', 'SITE_DESCRIPTION',
        'BG_INFO_MAIL', 'JOB_INFO_MAIL', 'DEPOT_INFO_MAIL', 
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

# Decode HTML (i.e. &uuml; -> ü, <br> -> \n)
@register.filter
def html_decode(value):
    # Add actual new-line character before HTML-decoding
    value = value.replace(u"<br />", u"<br />\\n")
    value = value.replace(u"<br/>",  u"<br />\\n")
    value = value.replace(u"<br>",   u"<br />\\n")
    value = value.replace(u"</p>",   u"</p>\\n")
    # Strip tags
    value = strip_tags(value)
    # HTML decode
    h = HTMLParser.HTMLParser()
    value = h.unescape(value)
    return value

# Decode HTML (i.e. &uuml; -> ü), then replace newline with newline+space
# to match the expected ICal formatting
@register.filter
def ical_escape(value):
    value = html_decode(value)
    # First convert all CLRF to CL only
    value = value.replace(u"\r\n", u"\n")
    # Then add CLRF newlines followed by one space for all breaks
    value = value.replace(u"\n", u"\r\n ")
    return value
