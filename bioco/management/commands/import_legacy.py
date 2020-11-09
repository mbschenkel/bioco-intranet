from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from juntagrico.entity.depot import Depot
from juntagrico.entity.member import Member

import traceback
import json

class Command(BaseCommand):
    help = 'Imports old bioco data'
    #
    # models_to_keep = [
    #     'auth.group',                             done
    #     'auth.user',                              done
    #     'my_ortoloco.abo',                        todo
    #     'my_ortoloco.loco',                       done, todo: Abo
    #     'my_ortoloco.depot',                      done
    #     'my_ortoloco.anteilschein',               todo
    #     'my_ortoloco.taetigkeitsbereich',         todo
    # ]

    def add_arguments(self, parser):
        parser.add_argument('db_file_name', type=str, help='A database dump optained with dumpdata to be imported')

    def handle(self, *args, **options):
        db_file_name = options['db_file_name']
        print(f"Opening {db_file_name}")
        with open(db_file_name, 'r') as infile:
            data = json.load(infile)

            self.run_import(data, 'auth.group',         'Group',    self.import_group)
            self.run_import(data, 'auth.user',          'User',     self.import_user)
            self.run_import(data, 'my_ortoloco.abo',    'Abo',      self.import_abo)     # must be before loco
            self.run_import(data, 'my_ortoloco.loco',   'Member',   self.import_member)  # must be after users
            self.run_import(data, 'my_ortoloco.depot',  'Depot',    self.import_depot)   # must be after importing members

    def run_import(self, data, model, title, command):
        for line in data:
            if line['model'] == model:
                try:
                    command(line)
                except:
                    print(f"{title} import failed for")
                    print(line)
                    raise

    def import_group(self, data):
        fields = data['fields']

        group = Group(pk=data['pk'])

        # intentionally not imported: group.permissions = []
        group.name = fields['name']
        group.save()

    def import_user(self, data):
        fields = data['fields']

        user = User(pk=data['pk'])
        user.email = fields['email']
        user.username = fields['username']
        user.date_joined = fields['date_joined']
        user.first_name = fields['first_name']
        user.last_name = fields['last_name']
        user.is_superuser = fields['is_superuser']
        user.is_staff = fields['is_staff']
        user.is_active = fields['is_active']
        user.last_login  = fields['last_login']
        user.password  = fields['password']

        user.save()

        # intentionally not imported: user.user_permissions = []
        print(fields['groups'])
        user.groups.set(fields['groups'])

    def import_abo(selfself, data):
        return

        abo = Abo(pk=data['pk'])

        # TODO this is now
        # -subscriptiontype
        # -subscriptionproduct
        # -subscriptionsize

        # old:
        # {'model': 'my_ortoloco.abo', 'fields': {'active': True, 'paid': True, 'depot': 16, 'groesse': 2, 'extra_abos': [], 'primary_loco': 42, 'number': '3'}, 'pk': 3}

        print(abo)

    def import_member(self, data):
        if data['pk'] == 1: return  # intranet admin
        fields = data['fields']

        member = Member(pk=data['pk'])
        member.first_name = fields['first_name']
        member.last_name = fields['last_name']
        member.email = fields['email']
        member.phone = fields['phone']
        member.mobile_phone = fields['mobile_phone']
        member.addr_street = fields['addr_street']
        member.addr_zipcode = fields['addr_zipcode']
        member.addr_location = fields['addr_location']
        member.birthday = "1900-01-01" # we dont have any recorded - fields['birthday']
        # not existing fields['sex']
        member.abo = None # todo properly match
        member.user = User.objects.get(pk=fields['user'])
        member.iban = '' # not existing
        member.confirmed = fields['confirmed']
        member.reachable_by_email = True
        member.canceled = False
        member.cancelation_date = None
        member.end_date = None
        member.inactive = False
        member.notes = ''

        member.save()

    def import_depot(self, data):
        fields = data['fields']
        depot = Depot()

        depot.name = fields['name']
        depot.code = fields['code']
        depot.addr_zipcode = fields['addr_zipcode']
        depot.addr_street = fields['addr_street']
        depot.addr_location = fields['addr_location']
        depot.contact = Member.objects.get(pk=fields['contact'])
        depot.weekday = fields['weekday']
        depot.description = ''
        depot.latitude = fields['latitude']
        depot.longitude = fields['longitude']

        depot.save()