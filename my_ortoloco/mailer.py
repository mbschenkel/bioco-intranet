# -*- coding: utf-8 -*-

from django.conf import settings
from django.core import mail
from django.template.loader import get_template
from django.template import Context
from django.core.mail import EmailMultiAlternatives
import re

#todo remove
#import logging
#FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
#logging.basicConfig(format=FORMAT, level=logging.DEBUG)
#dj only
#import logging
#logger = logging.getLogger(__name__)


#single point of change, todo check settings.DEFAULT_FROM_EMAIL
#(maybe move to settings and adjust address itself)
SENDER_EMAIL_ADDRESS = 'test@bioco.ch'

# sends mail only to specified email-addresses if dev mode
def send_mail(subject, message, from_email, to_emails):
    print 'send_mail from ' + SENDER_EMAIL_ADDRESS
    okmails = []
    if settings.DEBUG is False:
        pass
        #todo re-enable when stable.... okmails = to_emails
    else:
        #todo: not tested
        okmails.append(settings.DEBUG_EMAIL_ADDRESS)
        message =  ',<br/>'.join(to_emails) + message

    if len(okmails) > 0:
        for amail in okmails:
            res = mail.send_mail(subject, message, from_email, [amail], fail_silently=False)
            # todo: log errors
            print 'sending mail from ' + from_email + ' to ' + email 
            print ' res= ', res
        print "Mail sent to " + ", ".join(okmails) + (", on whitelist" if settings.DEBUG else "")

    return None


def send_mail_multi(email_multi_message):
    print 'send_mail_multi from ' + SENDER_EMAIL_ADDRESS
    okmails = []
    if settings.DEBUG is False:
        pass
        #todo re-enable when stable.... okmails = email_multi_message.to
        #     also below!
    else:
        #todo improve, dirty hack to modify meassage, by just duplicating it...
        okmails.append(settings.DEBUG_EMAIL_ADDRESS)
        modif_message = email_multi_message.alternatives[0][0] + '<br/>Intended for: <br/>'
        modif_message += u'<br/>-'.join(email_multi_message.to)
        email_multi_message.attach_alternative(modif_message, "text/html")
        
    if len(okmails) > 0:
        email_multi_message.to = []
        email_multi_message.bcc = [settings.DEBUG_EMAIL_ADDRESS]
        res = email_multi_message.send()
        # todo: log errors
        print "res = ", res
        print "Mail sent to " + ", ".join(okmails) + (", on whitelist" if settings.DEBUG else "")
    return None


def send_new_loco_in_taetigkeitsbereich_to_bg(area, loco):
    send_mail('Neues Mitglied im Taetigkeitsbereich ' + area.name,
              'Soeben hat sich ' + loco.first_name + " " + loco.last_name + ' in den Taetigkeitsbereich ' + area.name + ' eingetragen', SENDER_EMAIL_ADDRESS, [area.coordinator.email])


def send_contact_form(subject, message, loco, copy_to_loco):
    send_mail('Anfrage per my.ortoloco: ' + subject, message, loco.email, [SENDER_EMAIL_ADDRESS])
    if copy_to_loco:
        send_mail('Anfrage per my.ortoloco: ' + subject, message, loco.email, [loco.email])


def send_welcome_mail(email, password, server):
    plaintext = get_template('mails/welcome_mail.txt')
    htmly = get_template('mails/welcome_mail.html')

    # reset password so we can send it to him
    d = Context({
        'subject': 'Willkommen bei ortoloco',
        'username': email,
        'password': password,
        'serverurl': "http://" + server
    })

    text_content = plaintext.render(d)
    html_content = htmly.render(d)

    msg = EmailMultiAlternatives('Willkommen bei ortoloco', text_content, SENDER_EMAIL_ADDRESS, [email])
    msg.attach_alternative(html_content, "text/html")
    send_mail_multi(msg)


def send_been_added_to_abo(email, password, name, anteilsscheine, hash, server):
    plaintext = get_template('mails/welcome_added_mail.txt')
    htmly = get_template('mails/welcome_added_mail.html')

    # reset password so we can send it to him
    d = Context({
        'subject': 'Willkommen bei ortoloco',
        'username': email,
        'name': name,
        'password': password,
        'hash': hash,
        'anteilsscheine': anteilsscheine,
        'serverurl': "http://" + server
    })

    text_content = plaintext.render(d)
    html_content = htmly.render(d)

    msg = EmailMultiAlternatives('Willkommen bei ortoloco', text_content, SENDER_EMAIL_ADDRESS, [email])
    msg.attach_alternative(html_content, "text/html")
    send_mail_multi(msg)


def send_filtered_mail(subject, message, text_message, emails, server):
    plaintext = get_template('mails/filtered_mail.txt')
    htmly = get_template('mails/filtered_mail.html')

    htmld = Context({
        'subject': subject,
        'content': message,
        'serverurl': "http://" + server
    })
    textd = Context({
        'subject': subject,
        'content': text_message,
        'serverurl': "http://" + server
    })

    text_content = plaintext.render(textd)
    html_content = htmly.render(htmld)

    msg = EmailMultiAlternatives(subject, text_content, SENDER_EMAIL_ADDRESS, emails)
    msg.attach_alternative(html_content, "text/html")
    send_mail_multi(msg)


def send_politoloco_mail(subject, message, text_message, emails, server):
    plaintext = get_template('mails/politoloco.txt')
    htmly = get_template('mails/politoloco.html')

    htmld = Context({
        'subject': subject,
        'content': message,
        'serverurl': "http://" + server
    })
    textd = Context({
        'subject': subject,
        'content': text_message,
        'serverurl': "http://" + server
    })

    text_content = plaintext.render(textd)
    html_content = htmly.render(htmld)

    msg = EmailMultiAlternatives(subject, text_content, SENDER_EMAIL_ADDRESS, emails)
    msg.attach_alternative(html_content, "text/html")
    send_mail_multi(msg)


def send_mail_password_reset(email, password, server):
    plaintext = get_template('mails/password_reset_mail.txt')
    htmly = get_template('mails/password_reset_mail.html')
    subject = 'Dein neues ortoloco Passwort'

    htmld = Context({
        'subject': subject,
        'email': email,
        'password': password,
        'serverurl': "http://" + server
    })
    textd = Context({
        'subject': subject,
        'email': email,
        'password': password,
        'serverurl': "http://" + server
    })

    text_content = plaintext.render(textd)
    html_content = htmly.render(htmld)

    msg = EmailMultiAlternatives(subject, text_content, SENDER_EMAIL_ADDRESS, [email])
    msg.attach_alternative(html_content, "text/html")
    send_mail_multi(msg)


def send_job_reminder(emails, job, participants, server):
    plaintext = get_template('mails/job_reminder_mail.txt')
    htmly = get_template('mails/job_reminder_mail.html')

    d = Context({
        'job': job,
        'participants': participants,
        'serverurl': "http://" + server
    })

    text_content = plaintext.render(d)
    html_content = htmly.render(d)

    msg = EmailMultiAlternatives("ortoloco - Job-Erinnerung", text_content, SENDER_EMAIL_ADDRESS, emails)
    msg.attach_alternative(html_content, "text/html")
    send_mail_multi(msg)
