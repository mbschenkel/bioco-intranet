# -*- coding: utf-8 -*-
from my_ortoloco.models import *

taetigkeitsbereiche = [ 

###  CORE  ###

{
'name':            u'Ernten und Verpacken',
'core':            True,
'hidden':          False,
'coordinator':     u'Fassbind',
'description':     u'''Hier geht es ums Ernten, Abpacken und Verteilen.
Du hilfst dabei sicherzustellen, dass das Gemüse für die wöchentlichen Lieferungen pünktlich bereitsteht.''',
},
{
'name':            u'Verteilfahrten',
'core':            True,
'hidden':          False,
'coordinator':     u'Fassbind',
'description':     u'''Hier geht es um die wöchentlichen Verteilfahrten.
Du hilfst dabei sicherzustellen, dass die wöchentlichen Lieferungen pünktlich und regelmässig erfolgen.
Dieser Bereich richtet sich insbesondere an Mitglieder, die dazu auf ein Auto zurückgreifen können.''',
},
{
'name':            u'Feldarbeit',
'core':            True,
'hidden':          False,
'coordinator':     u'Köhnken',
'description':     u'''Hier geht es ums Pflanzen, Jäten und Hacken auf dem Acker ausserhalb des wöchentlichen Verteilrhythmus.''',
},

###  NON-CORE  ###

{
'name':            u'Infrastruktur',
'core':            False,
'hidden':          False,
'coordinator':     u'Köhnken',
'description':     u'''Hier gehts ums Werken, Zimmern und Konstruieren.
Z.B. der Unterhalt von Werkzeugen, Tunnels und Zäunen oder das Erstellen eines Abpackraumes.''',
},
{
'name':            u'Depot Betreuung',
'core':            False,
'hidden':          False,
'coordinator':     u'Eichenberger',
'description':     u'''Hier gehts um die Betreuung eines oder der Depots.''',
},
{
'name':            u'Web, IT, Grafik und Marketing',
'core':            False,
'hidden':          False,
'coordinator':     u'Tsianou',
'description':     u'''Hier geht es ums Gestalten von Flyern, Schreiben von Texten und Pflegen der Webseite und des Intranets.''',
},
{
'name':            u'Events',
'core':            False,
'hidden':          False,
'coordinator':     u'Zehnder-Knaus',
'description':     u'''Hier geht es ums Organisieren von einmaligen und regelmässigen Anlässen.''',
},
{
'name':            u'Administratives',
'core':            False,
'hidden':          False,
'coordinator':     u'Zehnder-Knaus',
'description':     u'''Hier geht es ums Organisieren, die Administration und Koordination. Du hilfst mit sicherzustellen, dass bei biocò alles rund läuft.''',
},
{
'name':            u'Kochen',
'core':            False,
'hidden':          False,
'coordinator':     u'Zehnder-Knaus',
'description':     u'''Hier geht es ums Kochen, insb. vor und während Anlässen und Festen.''',
},
{
'name':            u'Kinderbetreuung',
'core':            False,
'hidden':          False,
'coordinator':     u'Zehnder-Knaus',
'description':     u'''Hier geht es um die Betreuung von Kindern, die während Einsätzen, Anlässen oder Festen auf den Hof mitkommen.''',
},

###  HIDDEN  ###

{
'name':            u'Spezialeinsätze',
'core':            False,
'hidden':          True,
'coordinator':     u'Schenkel',
'description':     u'''Sammelpool für alles unvorhergesehene, einmalige oder nicht zuordnungsbare.''',
},
{
'name':            u'Betriebsgruppe',
'core':            False,
'hidden':          True,
'coordinator':     u'Zehnder-Knaus',
'description':     u'''Für Mitglieder der Betriebsgruppe.''',
},
]

def create_taetigkeitsbereiche():
    print '***************************************************************'
    print 'Creating Taetigkeitsbereiche'
    print '***************************************************************'
        
    for d in taetigkeitsbereiche:
        print ('Creating TB %s' % d["name"]).encode('utf8')
        d["coordinator"] = Loco.objects.filter(last_name__contains=d["coordinator"]).first()
        obj = Taetigkeitsbereich(**d)
        obj.save()
