from django.core.management.base import BaseCommand, CommandError

from my_ortoloco.models import *
from my_ortoloco.model_audit import *

from django.contrib.auth.models import *
from my_ortoloco.views import password_generator
from my_ortoloco.mailer import *

# Console script to send new password to all users who have never logged in
class Command(BaseCommand):

    # entry point used by manage.py
    def handle(self, *args, **options):
        locos = Loco.objects.all()
        for loco in locos:
            if (loco.user.date_joined - loco.user.last_login).seconds:
                print "[DONT SEND]  ", loco, loco.user.date_joined, '=', loco.user.last_login
            else:
                print "[SEND NEW PW]", loco, loco.user.date_joined
                pw = password_generator()
                loco.user.set_password(pw)
                loco.user.save()
                send_mail_password_reset(loco.email, pw, "intranet.bioco.ch")
                return
                