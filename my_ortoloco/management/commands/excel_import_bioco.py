# -*- coding: utf-8 -*-

#use as
#./manage.py clean_db
#./manage.py excel_import_bioco ../data/bioco_init_data_20140714.xlsx 2>&1 | tee -a import_log.txt | less

from django.core.management.base import BaseCommand, CommandError

from my_ortoloco.models import *
from my_ortoloco.model_audit import *

from django.contrib.auth.models import Permission, Group
from django.contrib.auth.models import User
from django.contrib.auth.models import *

#excel read
import xlrd 

import traceback
from string import Template
from datetime import datetime

from _create_taetigkeitsbereiche import create_taetigkeitsbereiche
from _create_jobtyps import create_jobtyps

class Command(BaseCommand):
    args = '<file-name>'
    help = 'Read Excel file containing all members and import them'
    
    # hard coded fromat
    LOCO_SHEET_NAME = u'Mitglieder'
    DEPOT_SHEET_NAME = u'Depots'
    SKIP_ROWS = 2 # skip lines (0: stand) and B(1: header)
    
    # row format in loco-table, 0-based
    LOCO_FIRST_NAME_ROW = 0
    LOCO_LAST_NAME_ROW = 1
    LOCO_SEX_ROW = 2
    LOCO_STREET_ROW = 3
    LOCO_CITY_ROW = 4 # incl. ZIP
    LOCO_EMAIL_ROW = 5
    LOCO_TEL_ROW = 6
    LOCO_MOBILE_ROW = 7
    LOCO_STATUS = 8
    LOCO_ABO_ID_ROW = 9
    LOCO_SIZE = 10
    LOCO_DEPOT_ROW = 11
    LOCO_ANTEILSSCHEIN = 14
    
    # row format in depot-table, 0-based
    # id = 0, ignoring
    DEPOT_ABBREV_ROW = 1
    DEPOT_NAME = 2
    DEPOT_DAY = 3
    DEPOT_ADDR = 4
    DEPOT_ZIP = 5
    DEPOT_CITY = 6
    DEPOT_LAT = 7
    DEPOT_LONG = 8
    DEPOT_RESP_LOCO = 9
    
    # keep a list
    new_locos = []
    
    # entry point used by manage.py
    def handle(self, *args, **options):
        self.stdout.write('Excel read')
        
        assert User.objects.all().count() == 1
        
        for file_name in args:
            self.stdout.write('Reading from file "' + file_name + '"')
            workbook = xlrd.open_workbook(file_name)
            loco_worksheet = workbook.sheet_by_name(self.LOCO_SHEET_NAME)
            depot_worksheet = workbook.sheet_by_name(self.DEPOT_SHEET_NAME)
            
            #TODO also create access-right-groups (Betriebsgruppe, Depotadmin, ...)
            #     and assign people as staff
            
            # from excel
            print 'loco_worksheet=', self.LOCO_SHEET_NAME
            self.import_locos(loco_worksheet)
            
            print 'depot_worksheet=', self.DEPOT_SHEET_NAME
            self.import_depots(depot_worksheet)
            
            # abos depend on depots, so do this now
            self.assign_abos()
            self.assign_anteilsscheine()
            self.assign_rights()
            self.add_permissions()
            
            # constant fixtures (require locos to exist)
            create_taetigkeitsbereiche()
            create_jobtyps()
            
    def import_depots(self, worksheet):
        print '***************************************************************'
        print 'Importing Depots'
        print '***************************************************************'

        num_rows = worksheet.nrows 
        print 'Going to import depot-table with %s rows' % (num_rows - self.SKIP_ROWS)
        for row in range(self.SKIP_ROWS, num_rows):
            try:
                d_name = worksheet.cell_value(row, self.DEPOT_NAME)
                res = Depot.objects.filter(name=d_name)
                if 0 < res.count():
                    print (u'A depot with name %s is already known, ignoring      ******' % d_name).encode('utf-8')
                    continue

                d = Depot()
                d.code = worksheet.cell_value(row, self.DEPOT_ABBREV_ROW)
                d.name = d_name
                d.weekday = worksheet.cell_value(row, self.DEPOT_DAY)
                d.latitude = worksheet.cell_value(row, self.DEPOT_LAT)
                d.longitude = worksheet.cell_value(row, self.DEPOT_LONG)
                d.addr_street = worksheet.cell_value(row, self.DEPOT_ADDR)
                d.addr_zipcode = unicode(int(worksheet.cell_value(row, self.DEPOT_ZIP)))
                d.addr_location = worksheet.cell_value(row, self.DEPOT_CITY)
                
                resp_name = worksheet.cell_value(row, self.DEPOT_RESP_LOCO)
                res = Loco.objects.filter(last_name__contains=resp_name)
                if 0 < res.count():
                    res = res[0]
                    print (u'A loco with name %s similar to %s was found, use as responsible' % (res, resp_name)).encode('utf-8')
                else:
                    #res = Loco.objects.get(pk=1)
                    res = Loco.objects.filter(last_name__contains='Schenkel').first()
                    print (u'A loco with name similar to %s was not found, use #1 as responsible    ********' % resp_name).encode('utf-8')
                d.contact = res
            
                d.save()
                print (u'Depot %s created' % d.name).encode('utf-8')
                
            except Exception, e:
                print u'Error in depot row %d   ********' % row
                traceback.print_exc()
                #raise e
    
    
    def import_locos(self, worksheet):
        print '***************************************************************'
        print 'Importing Locos'
        print '***************************************************************'
    
        num_rows = worksheet.nrows 
        print u'Going to import loco-table with %s rows' % (num_rows - self.SKIP_ROWS)
        for row in range(self.SKIP_ROWS, num_rows):
            try:
                #for i in range(0, self.LOCO_ANTEILSSCHEIN):
                #    if worksheet.cell(row, i).ctype is xlrd.XL_CELL_TEXT:
                #        print worksheet.cell(row, i).value.encode('utf-8')
                #    else:
                #        print row, i, worksheet.cell_value(row, i), '(float)'
                    
                l = new_loco()
                l.first_name = worksheet.cell_value(row, self.LOCO_FIRST_NAME_ROW).strip()
                l.last_name = worksheet.cell_value(row, self.LOCO_LAST_NAME_ROW).strip()
                
                if worksheet.cell_value(row, self.LOCO_SEX_ROW).strip() in [u'Herr']:
                    l.sex = 'M'
                else:
                    l.sex = 'F'
                l.street = worksheet.cell_value(row, self.LOCO_STREET_ROW).strip()
                l.set_zip_city(worksheet.cell(row, self.LOCO_CITY_ROW).value.strip())
                l.email = worksheet.cell_value(row, self.LOCO_EMAIL_ROW).strip()
                l.tel = worksheet.cell_value(row, self.LOCO_TEL_ROW).strip()
                l.mobile_phone = worksheet.cell_value(row, self.LOCO_MOBILE_ROW).strip()
                l.abo_id = unicode(worksheet.cell_value(row, self.LOCO_ABO_ID_ROW))
                l.depot = worksheet.cell_value(row, self.LOCO_DEPOT_ROW).strip()
                l.abo_size = worksheet.cell_value(row, self.LOCO_SIZE).strip()
                l.anteilsschein = worksheet.cell_value(row, self.LOCO_ANTEILSSCHEIN)
                l.birthday = u''

                l.print_out()
                
                l.status = worksheet.cell_value(row, self.LOCO_STATUS).strip()
                if l.status not in [u'B', u'b', u'G', u'g']:
                    print (u'Status is %s and not B or G - skipping' % (l.status)).encode('utf-8')
                    continue
                                
                l.insert()
                self.new_locos.append(l)
            #except IOError :
            except Exception, e:
                print 'exc:', e
                print 'Error in loco row %d' % row
                traceback.print_tb(e)
                print '--- end of traceback ---'
                #raise e

    # treat some people in a special way...            
    def assign_rights(self):
        print '***************************************************************'
        print 'Assigning rights'
        print '***************************************************************'
    
        ms_loco = Loco.objects.filter(last_name__contains='Schenkel')
        ms_user = User.objects.filter(username__contains='Schenkel')
        admin_user = User.objects.filter(username__contains='admin')
        if 1 == ms_loco.count() and 1 == admin_user.count():
            print 'Found Schenkel, assigning to admin'
            ms_loco = ms_loco[0]
            admin_user = admin_user[0]
            ms_loco.user = admin_user
            ms_loco.save()
            if 1 == ms_user.count():
                ms_user = ms_user[0]
                print 'deleted user ms'
                ms_user.delete()
           
    def add_permissions(self):
        print '***************************************************************'
        print 'Adding Permissions'
        print '***************************************************************'

        # add bg group
        apps = ("static_ortoloco", "my_ortoloco", "photologue")
        perms = Permission.objects.filter(content_type__app_label__in=apps)
        g = Group(name="Betriebsgruppe")
        g.save()
        g = Group.objects.get(name="Betriebsgruppe")
        g.permissions = perms
        g.save()
        
    def assign_anteilsscheine(self):
        print '***************************************************************'
        print 'Assigning Anteilsscheine'
        print '***************************************************************'
        for new_loco in self.new_locos:
            new_loco.assign_anteilsschein()

    def assign_abos(self):
        print '***************************************************************'
        print 'Assigning abos'
        print '***************************************************************'
        for new_loco in self.new_locos:
            new_loco.assign_abo()

class new_loco(object):
    first_name = ''
    last_name = ''
    street = ''
    zip = ''
    city = ''
    email = ''
    tel = ''
    mobile_phone = ''
    abo_id = ''
    depot = ''
    abo_size = ''
    anteilsschein = ''
    birthday = ''
    status = ''
    
    zip_city_re = re.compile('(^[0-9]{4,5})\s(.*$)')
    
    def set_zip_city(self, zip_city):
        #print 'set_zip_city:', zip_city.encode('utf-8')
        try:
            r = self.zip_city_re.match(zip_city)
            self.zip = r.group(1)
            self.city = r.group(2)
        except:
            self.zip = u'0000'
            self.city = u'unknown'
    
    def insert(self):
        res = Loco.objects.filter(email=self.email)
        if 0 < res.count():
            print (u'A loco with email %s is already known, adding "+doppelt"    ********' % self.email).encode('utf-8')
            self.email = self.email.replace('@', '+doppelt@')
        l = Loco()
        l.first_name = self.first_name
        l.last_name = self.last_name
        l.sex = self.sex
        if self.street:
            l.addr_street = self.street
        else:
            l.addr_street = '[unknown]'
        l.addr_zipcode = self.zip
        l.addr_location = self.city
        if self.email:
            l.email = self.email
        else:
            print (u'No email address, using dummy %s"    ********' % self.email).encode('utf-8')
            l.email = 'dummy____' + l.last_name + '@bioco.ch'
        if self.tel:
            l.phone = self.tel
        else:
            l.phone = '0' # can not be blank
        if self.mobile_phone:
            l.mobile_phone = self.mobile_phone
        else:
            l.mobile_phone = ''
        
        if self.birthday:
            l.birthday = datetime.strptime(self.birthday, '%d.%m.%Y') 
        else:
            l.birthday = datetime(1900, 1, 1, 0, 0, 0) 
        
        try:
            l.full_clean()
        except ValidationError as e:
            # Do something based on the errors contained in e.message_dict.
            # Display them to a user, or handle them programmatically.
            print 'Validation error:', e.message_dict
            pass
        
        l.save()
        
    def assign_anteilsschein(self):
        loco = Loco.objects.get(email=self.email)
        print self.last_name.encode('utf-8'), int(self.anteilsschein)
        for i in range(int(self.anteilsschein)):
            antsch = Anteilschein(loco=loco, paid=False, canceled=False)
            antsch.save()
    
    def assign_abo(self):
        abo_id = unicode(self.abo_id)
        if not abo_id:
            print 'ignoring empty abo id', abo_id
            return
        # convert Bx abos of betriebsgruppe to 100x numbers
        abo_id = abo_id.replace('B', '100')
        abo_id = int(float(abo_id))
        self.abo_id = abo_id
        
        loco = Loco.objects.get(email=self.email)
        
        a = Abo.objects.filter(pk=abo_id)
        if 0 == a.count():
            d = Depot.objects.filter(name__contains=self.depot)
            if (not self.depot) or (not d.count()):
                print (u'No depot "%s" found, using Geisshof  *********' % self.depot).encode('utf-8')
                d = Depot.objects.filter(name__contains='Geisshof')
            a = Abo(id=abo_id)
            a.depot = d.first()
            a.active = True
            a.primary_loco = loco
            if self.abo_size == 'N':
                a.groesse = int(2)
            elif self.abo_size == 'G':
                a.groesse = int(4)
            else:
                a.groesse = int(1)
            print (u"No abo with number %s found, creating one of size %s (%d) for %s" % (abo_id, self.abo_size, a.groesse, loco)).encode('utf-8')
            a.save()
            loco.abo = a
            loco.save()
            if self.status in [u'B', u'b']: #abo_id > 900:
                print u'User assigned to staff!!!'
                loco.user.is_staff = True
                loco.user.save()
        else:
            print (u"Abo with number %s found, using it for %s" % (abo_id, loco)).encode('utf-8')
            a = a[0]
            if not a.primary_loco:
                print "Primary was not assigned, doing so now   ************"
                a.primary_loco = loco
                #a.groesse = int(self.abo_size)
                a.save()
            
            loco.abo = a
            loco.save()

        
    def print_out(self):
        s = u'%s %s from %s (%s) with Abo id %s' % (self.first_name, self.last_name, self.city, unicode(self.zip), unicode(self.abo_id))
        print s.encode('utf-8')
