from django.core.management.base import BaseCommand, CommandError

from my_ortoloco.models import *
from my_ortoloco.model_audit import *

from django.contrib.auth.models import *
from my_ortoloco.views import password_generator
from my_ortoloco.mailer import *

# Console script to send new password to all users who have never logged in
class Command(BaseCommand):
    args = '(a|b|l)'
    help = 'Send new password for all users that never logged in (a=all, b=BG, l=non-BG)'

    # entry point used by manage.py
    def handle(self, *args, **options):
        option = args[0]
        if option == 'a':
            print 'A: All locos'
            locos = Loco.objects.all()
        elif option == 'b':
            print 'B: BG-locos only'
            locos = Loco.objects.filter(user__is_staff=True)
        elif option == 'l':
            print 'L: Non-BG locos only'
            locos = Loco.objects.all(user__is_staff=False)
        else:
            print 'Use either a=all, b=BG, l=non-BG-Locos'
            locos = ()
            
        for loco in locos:
            if not loco.user:
                print loco, 'continue......................................................................'
                continue
                
            if (loco.user.date_joined - loco.user.last_login).seconds:
                print "[DONT SEND]  ", loco, loco.user.date_joined, '=', loco.user.last_login
            else:
                print "[SEND NEW PW]", loco, loco.user.date_joined
                pw = password_generator()
                loco.user.set_password(pw)
                loco.user.save()
                send_mail_password_reset(loco.email, pw, "intranet.bioco.ch")
                