# -*- coding: utf-8 -*-

#use as
#./manage.py delete_job_data;
#./manage.py import_old_jobs ../data/xxxx.xlsx 2>&1 | tee -a ../import_jobs_log.txt | less



from django.core.management.base import BaseCommand, CommandError

from my_ortoloco.models import *
from my_ortoloco.model_audit import *

from django.contrib.auth.models import Permission, Group
from django.contrib.auth.models import User
from django.contrib.auth.models import *

#excel read
import xlrd 
import random
import string
import traceback
from string import Template
from datetime import datetime

from _create_taetigkeitsbereiche import create_taetigkeitsbereiche
from _create_jobtyps import create_jobtyps

class Command(BaseCommand):
    args = '<file-name>'
    help = 'Read Excel file containing all members and import them'
   
    # entry point used by manage.py
    def handle(self, *args, **options):
        self.stdout.write('Excel read')
        for file_name in args:
            i = Intranet(file_name)
            i.readFile()
            i.importAll()
        self.stdout.write('We are done!')

class Event:
    def __init__(self, worksheet, row):
        #active, cancelled, category 3,
        #description, date, startTime 6,
        #endTime, noPeopleReq, carReq 9, 
        #*subscribers = row
        self.dict = dict()
        self.dict['number'] = row
        self.dict['active'] = int(worksheet.cell_value(row, 0))
        self.dict['category'] = worksheet.cell_value(row, 2).strip()
        self.dict['description'] = worksheet.cell_value(row, 3).strip()
        self.dict['date'] = worksheet.cell_value(row, 4).strip()
        startTime = worksheet.cell_value(row, 5)
        self.dict['startTime'] = self.formatTime(startTime)
        endTime = worksheet.cell_value(row, 6)
        self.dict['endTime'] = self.formatTime(endTime)
        self.dict['noPeopleReq'] = int(worksheet.cell_value(row, 7))
        carReq = int(worksheet.cell_value(row, 8))
        if carReq == 1.0:
            carReqText = 'Ja'
        else:
            carReqText = 'Nein'
        self.dict['carReq'] = carReq
        self.dict['carReqText'] = carReqText
            
        cancelled = int(worksheet.cell_value(row, 1))
        if -1.0 == cancelled:
            statusText = '<span style="color: #ff0000;">Abgesagt</span>'
        elif 1.0 == cancelled:
            statusText = '<span style="color: #00ff00;">Best&auml;tigt</span>'
        else:
            statusText = ''
            
        self.dict['cancelled'] = cancelled
        self.dict['statusText'] = statusText
        subscribers = []
        for subsc_col in range(9, worksheet.ncols):
            subsc = worksheet.cell_value(row, subsc_col).strip()
            if subsc:
                subscribers.append(subsc)
        self.dict['subscribers'] = subscribers
        
        self.MAX_PEOPLE = 7
        #self.printInfo()
        
    def formatTime(self, t):
        try:
            res = time.gmtime(float(t)*24*60*60)
            res = time.strftime('%H:%M', res)
        except:
            res = t
        return res
        
    def printInfo(self):
        print('=== Event ==')
        for key in self.dict:
            value=self.dict[key]
            print('  ', key, '=', value)
        
    def getBereich(self):
        our_name = u'Import aus altem Intranet'
        ber = Taetigkeitsbereich.objects.filter(name=our_name)
        if ber.count():
            #print u'Found Taetigkeitsbereich %s' % our_name
            ber = ber[0]
        else:
            print u'+++ Creating Taetigkeitsbereich %s' % our_name
            ber = Taetigkeitsbereich()
            ber.name = our_name
            ber.description = u'Sammelbecken für alle Importierten Einsätze'
            ber.core = False
            ber.hidden = True
            ber.coordinator = Loco.objects.filter(last_name__contains='Schenkel')[0]
            ber.save()
        return ber
        
    def convertDate(self, text):
        #print (u'converting date %s' % text).encode('utf-8')
        parts = text.replace('.', '').split(" ")
        #print 'parts: ', " | ".join(parts)
        
        failed = False
        try:
            day = parts[1].replace('.', '').strip()
            day = int(day)
        except ValueError:
            #print (u'Day %s not a number' % parts[1]).encode('utf-8')
            failed = True
            
        month = parts[2].lower()
        if u'mär' in month:
            month = 3
        elif u'mar' in month:
            month = 3
        elif u'apr' in month:
            month = 4
        elif u'mai' in month:
            month = 5
        elif u'jun' in month:
            month = 6
        elif u'jul' in month:
            month = 7
        elif u'aug' in month:
            month = 8
        elif u'sep' in month:
            month = 9
        else:
            #print (u'Month %s not found' % parts[2]).encode('utf-8')
            failed = True
            
        if failed:
            print (u'--- Date could not be converted: %s' % text).encode('utf-8')
            return (text, datetime(2014, 1, 1, 0, 0, 0))
        else:
            the_date = datetime(2014, month, day, 0, 0, 0) 
            date_text = the_date.strftime('%Y-%m-%d')
            print (u'+++ Date converted: %s == %s' % (date_text, text)).encode('utf-8')
            return (date_text, the_date)
        
    def importLine(self):   
        date_text, the_date = self.convertDate(self.dict['date'])
        jt_name = 'Import #' + str(self.dict['number']) + ' ' + self.dict['category'] + ' (' + date_text + ')' 
        #jt_name += '_' + self.id_generator()
        print (u'Importing <%s>' % jt_name).encode('utf-8')
            
        subscriberList = ''
        subscribers = self.dict['subscribers']
        
        if not subscribers:
            print '=== No subscribers to job, skipping'
            return
            
        if -1 == self.dict['cancelled']:
            print '=== Job had been cancelled, skipping'
            return
            
        if the_date > datetime(2014, 8, 3, 23, 0, 0):
            print '=== Day is in or after new Intranet was introduced, skipping'
            return
        
        description  = u'<h4>Import aus altem Intranet</h4>'
        description += u'<b>Kategorie:</b> ' + self.dict['category'] + u'<br />\n'
        description += u'<b>Beschreibung:</b> ' + self.dict['description'] + u'<br />\n'
        description += u'<b>Kategorie:</b> ' + self.dict['category'] + u'<br />\n'
        description += u'<b>Datum:</b> ' + self.dict['date'] + u' von '
        description += self.dict['startTime'] + u' bis '
        description += self.dict['endTime'] + u'<br />\n'
        description += u'<b>Benötigt:</b> ' + str(self.dict['noPeopleReq']) + u' Helfer<br />\n'
        description += u'<b>Auto benötigt:</b> ' + self.dict['carReqText'] + u'<br />\n'
        description += u'<b>Teilnehmer:</b> ' + u', '.join(subscribers) + u'<br />\n'
        
        #generate jobtyp and job
        jt = JobTyp()
        jt.name = jt_name
        jt.displayed_name = jt_name
        jt.description = description
        jt.bereich = self.getBereich()
        jt.duration = 1
        jt.location = 'Geisshof'
        jt.car_needed = self.dict['carReq']
        jt.save()
        
        j = Job()
        j.typ = jt
        j.slots = max(self.dict['noPeopleReq'], len(subscribers))
        j.time = the_date
        j.reminder_sent = True
        j.save()
        
        #for i in range(self.MAX_PEOPLE):
        #    if i < len(subscribers):
        #        name = subscribers[i]
        for name in subscribers:
            parPos = name.find("(")
            if 0 < parPos:
                textInPar = name[parPos+1:name.find(")")]
            else:
                textInPar = u'--empty--'
            
            hasCar = (0 < name.find('mit Auto'))
            
            spacePos = name.find(" ")
            firstPart = name[0:spacePos]
            
            secondSpacePos = name.find(" ", spacePos+1)
            if 0 < secondSpacePos:
                secondPart = name[spacePos+1:secondSpacePos]
            else:
                secondPart = name[spacePos+1:]
            
            """
            print "fullName: <" + name.encode('utf-8') + ">"
            print "parPos: <" + str(parPos) + ">"
            print "spacePos: <" + str(spacePos) + ">"
            print "secondSpacePos: <" + str(secondSpacePos) + ">"
            print "textInPar: <" + textInPar.encode('utf-8') + ">"
            print "firstPart: <" + firstPart.encode('utf-8') + ">"
            print "secondPart: <" + secondPart.encode('utf-8') + ">"
            """
            
            firstPart = firstPart.strip()
            secondPart = secondPart.strip()
            
            found = False
            method = 'NOT FOUND'
            if not found and firstPart and secondPart:
                l = Loco.objects.filter(first_name__contains=firstPart, last_name__contains=secondPart)
                if 1 == l.count():
                    found = True
                    mark = u'+++'
                    method = u'FIRST-LAST'
            
            if not found and firstPart and secondPart:
                l = Loco.objects.filter(first_name__contains=secondPart, last_name__contains=firstPart)
                if 1 == l.count():
                    found = True
                    mark = u'+++'
                    method = u'LAST-FIRST'
            
            if not found and firstPart:
                l = Loco.objects.filter(first_name__contains=firstPart)
                if 1 == l.count():
                    found = True
                    mark = u'???'
                    method = u'FIRST-0'
                    
            if not found and secondPart:
                l = Loco.objects.filter(last_name__contains=secondPart)
                if 1 == l.count():
                    found = True
                    mark = u'???'
                    method = u'0-LAST'
                    
            if found:
                loco = l[0]
                print (u'{} Found (with {:10s})   {:25s}  ==  {}'.format(mark, method, loco, name)).encode('utf-8')
                if hasCar:
                    print(u'    --> With Car')
                b = Boehnli()
                b.job = j
                b.loco = loco
                b.with_car = hasCar
                b.save()                    
            else:
                print (u'--- Did not find              %s' % name).encode('utf-8')

                
    def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))


class Intranet:
    def __init__(self, inFile):
        self.inFileName = inFile
        self.events = list()
        
    def readHeaderFile(self):
        data = '';
        with open ("text.txt", "r") as myfile:
            data = myfile.read() #.replace('\n', '')
        return data

    def readFile(self):
        print('Reading file', self.inFileName)
        workbook = xlrd.open_workbook(self.inFileName)
        worksheet = workbook.sheet_by_name('Tabelle1')
        SKIP_ROWS = 1;
        nRows = worksheet.nrows
        ###TODO : 
        #nRows = 20
        #print('=== number of rows limited to {}'.format(nRows))
        print('Going to import table with rows {} to {}'.format( SKIP_ROWS, nRows))
        for row in range(SKIP_ROWS, nRows):
            try:
                self.events.append(Event(worksheet, row))
            except:
                print('Skipped line', row)

    def importAll(self):    
        for e in self.events:
            print u''
            print u'------------------------------------''------------------------------------'
            e.importLine()
            print u''
            
                                               