# -*- coding: utf-8 -*-
from my_ortoloco.models import *

taetigkeitsbereiche = [ 
{
'name':            u'Ernten und Verteilen',
'core':            True,
'hidden':          False,
'coordinator':     u'Schenkel',
'description':     u'''Hier geht es ums Ernten, Abpacken und Verteilen.
Du hilfst dabei sicherzustellen, dass die wöchentlichen Lieferungen pünktlich und regelmässig erfolgen.''',
},
{
'name':            u'Feldarbeit',
'core':            True,
'hidden':          False,
'coordinator':     u'Schenkel',
'description':     u'''Hier geht es ums Pflanzen, Jäten und Hacken auf dem Acker.''',
},
{
'name':            u'Spezialeinsäe',
'core':            False,
'hidden':          True,
'coordinator':     u'Schenkel',
'description':     u'''Sammelpool für alles unvorhergesehene, einmalige oder nicht zuordnungsbar.''',
},
{
'name':            u'Infrastruktur',
'core':            False,
'hidden':          True,
'coordinator':     u'Schenkel',
'description':     u'''Hier gehts ums Werken, Zimmern und Konstruieren.
Z.B. vom Abpackraum, von Werkzeugen, Tunnels und Zäunen.''',
},
{
'name':            u'Events',
'core':            False,
'hidden':          True,
'coordinator':     u'Schenkel',
'description':     u'''Hier geht es ums Organisieren von einmaligen und regelmäigen Anlässen.''',
},
{
'name':            u'IT und Marketing',
'core':            False,
'hidden':          True,
'coordinator':     u'Schenkel',
'description':     u'''Hier geht es ums Gestalten von Flyern, Schreiben von Texten und Pflegen der Webseite und des Intranets.''',
},
{
'name':            u'Administratives',
'core':            False,
'hidden':          True,
'coordinator':     u'Schenkel',
'description':     u'''Hier geht es ums Organisieren, um Marketing und Buchhaltung. Du hilfst mit sicherzustellen, dass bei biocò alles rund läuft.''',
},
]

def create_taetigkeitsbereiche():
    print '***************************************************************'
    print 'Creating Taetigkeitsbereiche'
    print '***************************************************************'
        
    for d in taetigkeitsbereiche:
        d["coordinator"] = Loco.objects.get(last_name__contains=d["coordinator"])
        obj = Taetigkeitsbereich(**d)
        obj.save()
