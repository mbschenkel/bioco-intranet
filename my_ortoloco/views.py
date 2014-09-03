# -*- coding: utf-8 -*-

from datetime import date
from StringIO import StringIO
import string
import random
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import auth
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import Group
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.core.management import call_command
from django import db
from django.db.models import Sum, Count

from my_ortoloco.models import *
from my_ortoloco.forms import *
from my_ortoloco.helpers import *
from my_ortoloco.filters import Filter
from my_ortoloco.mailer import *

import hashlib
from static_ortoloco.models import Politoloco
from static_ortoloco.models import StaticContent

from decorators import primary_loco_of_abo


def password_generator(size=8, chars=string.ascii_uppercase + string.digits): return ''.join(random.choice(chars) for x in range(size))


def getBohnenDict(request):
    loco = request.user.loco
    next_jobs = set()
    if loco.abo is not None:
        year = date.today().year
        userbohnen = Boehnli.objects.filter(loco=loco, job__time__lte=datetime.datetime.now(), job__time__year=year)
    
        loco_pk = loco.pk

        # todo: maybe extend this such that we show 
        #       (A) user-bohnen, (B) other-user-in-abo-bohnen (C) to-be-done-bohnen        
        bohnen_done = userbohnen.__len__()
        bohnen_required = Abo.abo_types[loco.abo.groesse].required_bohnen / loco.abo.locos.count()
        bohnenrange = range(0, max(bohnen_done, bohnen_required))

        next_jobs = Job.objects.filter(boehnli__loco=loco, time__gte=datetime.datetime.now()).order_by("time")
        
    else:
        bohnenrange = None
        userbohnen = []
        next_jobs = set()
        loco_pk = 0

    return {
        'loco_pk': loco_pk,
        'user': request.user,
        'bohnenrange': bohnenrange,
        'userbohnen': len(userbohnen),
        'next_jobs': next_jobs,
        'staff_user': request.user.is_staff,
        'politoloco': request.user.has_perm('static_ortoloco.can_send_newsletter')
    }


@login_required
def my_home(request):
    """
    Overview on myortoloco
    """

    if StaticContent.objects.all().filter(name='IntranetHome').__len__() > 0:
        info_text = StaticContent.objects.all().filter(name='IntranetHome')[0].content
    else:
        info_text = ''
    
    jobs = get_current_jobs()
    renderdict = getBohnenDict(request)
    renderdict.update({
        'info_text': info_text,
        'jobs': jobs[:9],
        'teams': Taetigkeitsbereich.objects.filter(hidden=False),
        'no_abo': request.user.loco.abo is None
    })

    return render(request, "myhome.html", renderdict)


@login_required
def my_job(request, job_id):
    """
    Details for a job
    """
    loco = request.user.loco
    job = get_object_or_404(Job, id=int(job_id))

    def check_int(s):
        if not s:
            return False
        if s[0] in ('-', '+'):
            return s[1:].isdigit()
        return s.isdigit()
            
    error = None
    send_mail = False
    if request.method == 'POST':
        num = request.POST.get("jobs")
        initial_number = Boehnli.objects.filter(job=job, loco=loco).count()
        prev_initial_number = request.POST.get("initial_number")
        with_car = request.POST.get("with_car", False)
        my_bohnen = job.boehnli_set.all().filter(loco=loco)
        if not check_int(num):
            # assume the user wanted to subscribe anyway
            num = 1
        if 0 >= int(num):
            error = "Ungueltige Anzahl Einschreibungen %s (mindestens 1)" % num
        elif int(num) > job.freie_plaetze():
            error = "Zu hohe Anzahl Anmeldungen oder der Einsatz ist bereits ausgebucht"
        elif int(prev_initial_number) != int(initial_number):
            print "prev:", prev_initial_number 
            print "now: ", initial_number 
            error = ("Es scheint, dass du dich zweimal nacheinander eingetragen hast. "
                     "Wir haben nur einen Eintrag vorgenommen. "
                     "Wenn du dich tatsächlich zweimal eintragen willst, klicke bitte jetzt erneut.")
        else:
            # adding new participants
            send_mail = True
            add = int(num)
            for i in range(add):
                bohne = Boehnli.objects.create(loco=loco, job=job, with_car=with_car)

    participants = []
    for bohne in Boehnli.objects.filter(job_id=job.id):
        if bohne.loco is not None:
            participants.append(bohne)
    
    if send_mail:
        send_job_signup([loco.email], job, participants, request.META["HTTP_HOST"])
    
    # number of own registration before form-submit, to prevent unintended, 
    # multiple registrations with refresh or double-clicks
    initial_number = Boehnli.objects.filter(job=job, loco=loco).count()
    renderdict = getBohnenDict(request)
    renderdict.update({
        'participants': participants,
        'job': job,
        'initial_number': initial_number,
        'slotrange': range(0, job.slots),
        'error': error
    });
    return render(request, "job.html", renderdict)


@login_required
def my_depot(request, depot_id):
    """
    Details for a Depot
    """
    depot = get_object_or_404(Depot, id=int(depot_id))

    renderdict = getBohnenDict(request)
    renderdict.update({
        'depot': depot
    });
    return render(request, "depot.html", renderdict)


@login_required
def my_participation(request):
    """
    Details for all areas a loco can participate
    """
    loco = request.user.loco
    my_areas = []
    success = False
    if request.method == 'POST':
        old_areas = set(loco.areas.all())
        new_areas = set(area for area in Taetigkeitsbereich.objects.filter(hidden=False)
                        if request.POST.get("area" + str(area.id)))
        if old_areas != new_areas:
            loco.areas = new_areas
            loco.save()
            for area in new_areas - old_areas:
                send_new_loco_in_taetigkeitsbereich_to_bg(area, loco)

        success = True

    for area in Taetigkeitsbereich.objects.filter(hidden=False):
        if area.hidden:
            continue
        my_areas.append({
            'name': area.name,
            'description': area.description,
            'checked': loco in area.locos.all(),
            'id': area.id,
            'core': area.core,
            'coordinator': area.coordinator
        })

    renderdict = getBohnenDict(request)
    renderdict.update({
        'areas': my_areas,
        'success': success
    })
    return render(request, "participation.html", renderdict)


@login_required
def my_pastjobs(request):
    """
    All past jobs of current user
    """
    loco = request.user.loco

    allebohnen = Boehnli.objects.filter(loco=loco)
    past_bohnen = []

    for bohne in allebohnen:
        if bohne.job.time < datetime.datetime.now():
            past_bohnen.append(bohne)

    renderdict = getBohnenDict(request)
    renderdict.update({
        'bohnen': past_bohnen
    })
    return render(request, "my_pastjobs.html", renderdict)


@permission_required('static_ortoloco.can_send_newsletter')
def send_politoloco(request):
    """
    Send politoloco newsletter
    """
    sent = 0
    if request.method == 'POST':
        emails = set()
        if request.POST.get("allpolitoloco"):
            for loco in Politoloco.objects.all():
                emails.add(loco.email)

        if request.POST.get("allortolocos"):
            for loco in Loco.objects.all():
                emails.add(loco.email)

        if request.POST.get("allsingleemail"):
            emails.add(request.POST.get("singleemail"))

        send_politoloco_mail(request.POST.get("subject"), request.POST.get("message"), request.POST.get("textMessage"), emails, request.META["HTTP_HOST"])
        sent = len(emails)
    renderdict = getBohnenDict(request)
    renderdict.update({
        'politolocos': Politoloco.objects.count(),
        'ortolocos': Loco.objects.count(),
        'sent': sent
    })
    return render(request, 'mail_sender_politoloco.html', renderdict)


@login_required
def my_abo(request):
    """
    Details for an abo of a loco
    """
    renderdict = getBohnenDict(request)
    if request.user.loco.abo:
        renderdict.update({
            'zusatzabos': request.user.loco.abo.extra_abos.all(),
            'mitabonnenten': request.user.loco.abo.bezieher_locos().exclude(email=request.user.loco.email),
            'primary': request.user.loco.abo.primary_loco.email == request.user.loco.email
        })
    renderdict.update({
        'loco': request.user.loco,
        'scheine': request.user.loco.anteilschein_set.count(),
        'scheine_unpaid': request.user.loco.anteilschein_set.filter(paid=False).count(),
    })
    return render(request, "my_abo.html", renderdict)


@primary_loco_of_abo
def my_abo_change(request, abo_id):
    """
    Ein Abo ändern
    """
    month = int(time.strftime("%m"))
    if month >= 7:
        next_extra = datetime.date(day=1, month=1, year=datetime.date.today().year + 1)
    else:
        next_extra = datetime.date(day=1, month=7, year=datetime.date.today().year)
    renderdict = getBohnenDict(request)
    renderdict.update({
        'loco': request.user.loco,
        'change_size': month <= 10,
        'change_extra': month != 6 and month != 12,
        'next_extra_abo_date': next_extra,
        'next_size_date': datetime.date(day=1, month=1, year=datetime.date.today().year + 1)
    })
    return render(request, "my_abo_change.html", renderdict)


@primary_loco_of_abo
def my_depot_change(request, abo_id):
    """
    Ein Abo-Depot ändern
    """
    saved = False
    if request.method == "POST":
        request.user.loco.abo.depot = get_object_or_404(Depot, id=int(request.POST.get("depot")))
        request.user.loco.abo.save()
        saved = True
    renderdict = getBohnenDict(request)
    renderdict.update({
        'saved': saved,
        'loco': request.user.loco,
        "depots": Depot.objects.all()
    })
    return render(request, "my_depot_change.html", renderdict)

@primary_loco_of_abo
def my_size_change(request, abo_id):
    # todo - currently not supported, adjust to new abo_types definition
    return


    """
    Eine Abo-Grösse ändern
    """
    saved = False
    if request.method == "POST":
        request.user.loco.abo.groesse = int(request.POST.get("abo"))
        request.user.loco.abo.save()
        saved = True
    renderdict = getBohnenDict(request)
    renderdict.update({
        'saved': saved,
        'groesse': request.user.loco.abo.groesse
    })
    return render(request, "my_size_change.html", renderdict)


@primary_loco_of_abo
def my_extra_change(request, abo_id):
    """
    Ein Extra-Abos ändern
    """
    saved = False
    if request.method == "POST":
        for extra_abo in ExtraAboType.objects.all():
            if request.POST.get("abo" + str(extra_abo.id)) == str(extra_abo.id):
                request.user.loco.abo.extra_abos.add(extra_abo)
                extra_abo.abo_set.add(request.user.loco.abo)
            else:
                request.user.loco.abo.extra_abos.remove(extra_abo)
                extra_abo.abo_set.remove(request.user.loco.abo)

            request.user.loco.abo.save()
            extra_abo.save()

        saved = True

    abos = []
    for abo in ExtraAboType.objects.all():
        if abo in request.user.loco.abo.extra_abos.all():
            abos.append({
                'id': abo.id,
                'name': abo.name,
                'selected': True
            })
        else:
            abos.append({
                'id': abo.id,
                'name': abo.name
            })
    renderdict = getBohnenDict(request)
    renderdict.update({
        'saved': saved,
        'loco': request.user.loco,
        "extras": abos
    })
    return render(request, "my_extra_change.html", renderdict)


@login_required
def my_team(request, bereich_id):
    """
    Details for a team
    """

    job_types = JobTyp.objects.all().filter(bereich=bereich_id)

    jobs = get_current_jobs().filter(typ=job_types)

    renderdict = getBohnenDict(request)
    renderdict.update({
        'team': get_object_or_404(Taetigkeitsbereich, id=int(bereich_id)),
        'jobs': jobs,
    })
    return render(request, "team.html", renderdict)


@login_required
def my_einsaetze(request):
    """
    All jobs to be sorted etc.
    """
    renderdict = getBohnenDict(request)

    jobs = get_current_jobs();
    renderdict.update({
        'jobs': jobs,
        'show_all': True
    })

    return render(request, "jobs.html", renderdict)


@login_required
def my_einsaetze_all(request):
    """
    All jobs to be sorted etc.
    """
    renderdict = getBohnenDict(request)
    jobs = Job.objects.all().order_by("time")
    renderdict.update({
        'jobs': jobs,
    })

    return render(request, "jobs.html", renderdict)


def my_signup(request):
    """
    Become a member of ortoloco
    """
    success = False
    agberror = False
    agbchecked = False
    userexists = False
    if request.method == 'POST':
        agbchecked = request.POST.get("agb") == "on"

        locoform = ProfileLocoForm(request.POST)
        if not agbchecked:
            agberror = True
        else:
            if locoform.is_valid():
                #check if user already exists
                if User.objects.filter(email=locoform.cleaned_data['email']).__len__() > 0:
                    userexists = True
                else:
                    #set all fields of user
                    #email is also username... we do not use it
                    password = password_generator()

                    loco = Loco.objects.create(first_name=locoform.cleaned_data['first_name'], last_name=locoform.cleaned_data['last_name'], email=locoform.cleaned_data['email'])
                    loco.sex = locoform.cleaned_data['sex']
                    loco.addr_street = locoform.cleaned_data['addr_street']
                    loco.addr_zipcode = locoform.cleaned_data['addr_zipcode']
                    loco.addr_location = locoform.cleaned_data['addr_location']
                    loco.phone = locoform.cleaned_data['phone']
                    loco.mobile_phone = locoform.cleaned_data['mobile_phone']
                    loco.save()

                    loco.user.set_password(password)
                    loco.user.save()
                    
                    #registration is not complete, but loco and user exist anyway, so we send mail now
                    send_welcome_mail(loco.email, loco, password, request.META["HTTP_HOST"])
                    send_welcome_mail(settings.BG_INFO_MAIL, loco, "<geheim>", request.META["HTTP_HOST"])

                    #log in to allow him to make changes to the abo
                    loggedin_user = authenticate(username=loco.user.username, password=password)
                    login(request, loggedin_user)
                    success = True
    
                    return redirect("/my/aboerstellen")
    else:
        locoform = ProfileLocoForm()

    renderdict = {
        'locoform': locoform,
        'success': success,
        'agberror': agberror,
        'agbchecked': agbchecked,
        'userexists': userexists
    }
    return render(request, "signup.html", renderdict)


@login_required
def my_add_loco(request, abo_id):
    scheineerror = False
    scheine = 1
    userexists = False
    if request.method == 'POST':
        adding_loco = request.user.loco
        locoform = ProfileLocoForm(request.POST)
        if User.objects.filter(email=request.POST.get('email')).__len__() > 0:
            userexists = True
        try:
            scheine = int(request.POST.get("anteilscheine"))
            scheineerror = scheine < 0
        except TypeError:
            scheineerror = True
        except  ValueError:
            scheineerror = True
        if locoform.is_valid() and scheineerror is False and userexists is False:
            username = make_username(locoform.cleaned_data['first_name'],
                                     locoform.cleaned_data['last_name'],
                                     locoform.cleaned_data['email'])
            pw = password_generator()
            loco = Loco.objects.create(first_name=locoform.cleaned_data['first_name'], last_name=locoform.cleaned_data['last_name'], email=locoform.cleaned_data['email'])
            loco.first_name = locoform.cleaned_data['first_name']
            loco.last_name = locoform.cleaned_data['last_name']
            loco.email = locoform.cleaned_data['email']
            loco.addr_street = locoform.cleaned_data['addr_street']
            loco.addr_zipcode = locoform.cleaned_data['addr_zipcode']
            loco.addr_location = locoform.cleaned_data['addr_location']
            loco.phone = locoform.cleaned_data['phone']
            loco.mobile_phone = locoform.cleaned_data['mobile_phone']
            loco.confirmed = False
            loco.abo_id = abo_id
            loco.save()

            loco.user.set_password(pw)
            loco.user.save()

            for num in range(0, scheine):
                anteilschein = Anteilschein(loco=loco, paid=False)
                anteilschein.save()

            send_been_added_to_abo(loco.email, pw, adding_loco.get_name(), scheine, hashlib.sha1(locoform.cleaned_data['email'] + str(abo_id)).hexdigest(), request.META["HTTP_HOST"])

            loco.save()
            if request.GET.get("return"):
                return redirect(request.GET.get("return"))
            return redirect('/my/aboerstellen')

    else:
        loco = request.user.loco
        initial = {"addr_street": loco.addr_street,
                   "addr_zipcode": loco.addr_zipcode,
                   "addr_location": loco.addr_location,
                   "phone": loco.phone,
        }
        locoform = ProfileLocoForm(initial=initial)
    
    renderdict = getBohnenDict(request)
    renderdict.update({
        'scheine': scheine,
        'userexists': userexists,
        'scheineerror': scheineerror,
        'locoform': locoform,
        "loco": request.user.loco,
        "depots": Depot.objects.all()
    })
    return render(request, "add_loco.html", renderdict)


@login_required
def my_createabo(request):
    """
    Abo erstellen
    """
    loco = request.user.loco
    scheineerror = False
    if loco.abo is None:
        selectedabo = Abo.SIZE_SMALL
    else:
        selectedabo = loco.abo.groesse
    
    """        
    if loco.abo is None or loco.abo.groesse is 1:
        selectedabo = "small"
    elif loco.abo.groesse is 2:
        selectedabo = "big"
    else:
        selectedabo = "house"
    """
    
    loco_scheine = 0
    if loco.abo is not None:
        for abo_loco in loco.abo.bezieher_locos().exclude(email=request.user.loco.email):
            loco_scheine += abo_loco.anteilschein_set.all().__len__()

    if request.method == "POST":
        scheine = int(request.POST.get("scheine"))
        selectedabo = int(request.POST.get("abo"))
        print 'selectedabo', selectedabo
        
        scheine += loco_scheine
        scheine_required = Abo.abo_types[selectedabo].min_anteilsscheine
        if scheine < scheine_required:
            scheineerror = True
        else:
            depot = Depot.objects.all().filter(id=request.POST.get("depot"))[0]
            if loco.abo is None:
                loco.abo = Abo.objects.create(groesse=selectedabo, primary_loco=loco, depot=depot)
            else:
                loco.abo.groesse = selectedabo
                loco.abo.depot = depot
            loco.abo.save()
            loco.save()

            if loco.anteilschein_set.count() < int(request.POST.get("scheine")):
                toadd = int(request.POST.get("scheine")) - loco.anteilschein_set.count()
                for num in range(0, toadd):
                    anteilschein = Anteilschein(loco=loco, paid=False)
                    anteilschein.save()

            if request.POST.get("add_loco"):
                return redirect("/my/abonnent/" + str(loco.abo_id))
            else:
                #registration completed
                return redirect("/my/willkommen")

    selected_depot = None
    mit_locos = []
    if request.user.loco.abo is not None:
        selected_depot = request.user.loco.abo.depot
        mit_locos = request.user.loco.abo.bezieher_locos().exclude(email=request.user.loco.email)

    renderdict = {
        'abo_types': Abo.abo_types,
        'loco_scheine': loco_scheine,
        "loco": request.user.loco,
        "depots": Depot.objects.all(),
        'selected_depot': selected_depot,
        "selected_abo": selectedabo,
        "scheineerror": scheineerror,
        "mit_locos": mit_locos
    }
    return render(request, "createabo.html", renderdict)


@login_required
def my_welcome(request):
    """
    Willkommen
    """

    renderdict = getBohnenDict(request)
    renderdict.update({
        'jobs': get_current_jobs()[:7],
        'teams': Taetigkeitsbereich.objects.filter(hidden=False),
        'no_abo': request.user.loco.abo is None
    })

    return render(request, "welcome.html", renderdict)


def my_confirm(request, hash):
    """
    Confirm from a user that has been added as a Mitabonnent
    """

    for loco in Loco.objects.all():
        if hash == hashlib.sha1(loco.email + str(loco.abo_id)).hexdigest():
            loco.confirmed = True
            loco.save()

    return redirect("/my/home")


@login_required
def my_contact(request):
    """
    Kontaktformular
    """
    loco = request.user.loco

    if request.method == "POST":
        # send mail to bg
        send_contact_form(request.POST.get("subject"), request.POST.get("message"), loco, request.POST.get("copy"))

    renderdict = getBohnenDict(request)
    renderdict.update({
        'usernameAndEmail': loco.first_name + " " + loco.last_name + " <" + loco.email + ">"
    })
    return render(request, "my_contact.html", renderdict)


@login_required
def my_profile(request):
    success = False
    loco = request.user.loco
    if request.method == 'POST':
        locoform = ProfileLocoForm(request.POST, instance=loco)
        if locoform.is_valid():
            #set all fields of user
            loco.sex = locoform.cleaned_data['sex']
            loco.first_name = locoform.cleaned_data['first_name']
            loco.last_name = locoform.cleaned_data['last_name']
            loco.email = locoform.cleaned_data['email']
            loco.addr_street = locoform.cleaned_data['addr_street']
            loco.addr_zipcode = locoform.cleaned_data['addr_zipcode']
            loco.addr_location = locoform.cleaned_data['addr_location']
            loco.phone = locoform.cleaned_data['phone']
            loco.mobile_phone = locoform.cleaned_data['mobile_phone']
            loco.save()

            success = True
    else:
        locoform = ProfileLocoForm(instance=loco)

    renderdict = getBohnenDict(request)
    renderdict.update({
        'locoform': locoform,
        'success': success
    })
    return render(request, "profile.html", renderdict)


@login_required
def my_change_password(request):
    success = False
    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['password'])
            request.user.save()
            success = True
    else:
        form = PasswordForm()

    renderdict = getBohnenDict(request)
    renderdict.update({
        'form': form,
        'success': success
    })
    return render(request, 'password.html', renderdict)


def my_new_password(request):
    sent = False
    if request.method == 'POST':
        sent = True
        locos = Loco.objects.filter(email=request.POST.get('username'))
        if len(locos) > 0:
            loco = locos[0]
            pw = password_generator()
            loco.user.set_password(pw)
            loco.user.save()
            send_mail_password_reset(loco.email, pw, request.META["HTTP_HOST"])

    renderdict = {
        'sent': sent
    }
    return render(request, 'my_newpassword.html', renderdict)


@staff_member_required
def my_mails(request):
    sent = 0
    if request.method == 'POST':
        emails = set()
        if request.POST.get("one_depot") == "on":
            the_depot = request.POST.get("the_depot")
            for loco in Loco.objects.filter(abo__depot=the_depot):
                emails.add(loco.email)
        if request.POST.get("one_area") == "on":
            the_area = request.POST.get("the_area")
            area = Taetigkeitsbereich.objects.filter(pk=the_area)[0]
            for loco in area.locos.all():
                emails.add(loco.email)
        if request.POST.get("allabo") == "on":
            for loco in Loco.objects.exclude(abo=None):
                emails.add(loco.email)
        if request.POST.get("allanteilsschein") == "on":
            for loco in Loco.objects.all():
                if loco.anteilschein_set.count() > 0:
                    emails.add(loco.email)
        if request.POST.get("all") == "on":
            for loco in Loco.objects.all():
                emails.add(loco.email)
        if len(emails) > 0:
            send_filtered_mail(request.POST.get("subject"), request.POST.get("message"), request.POST.get("textMessage"), emails, request.META["HTTP_HOST"])
            sent = len(emails)
            
    all_depots = Depot.objects.all()
    all_areas = Taetigkeitsbereich.objects.all()
    renderdict = getBohnenDict(request)
    renderdict.update({
        'sent': sent,
        'all_areas': all_areas,
        'all_depots': all_depots,
        'mail_is_live': settings.DEBUG
    })
    return render(request, 'mail_sender.html', renderdict)


#@staff_member_required
@login_required
def my_filters(request):
    renderdict = getBohnenDict(request)
    locos = Loco.objects.select_related('abo').select_related('abo__depot').all()
    renderdict.update({
        'locos': locos
    })
    return render(request, 'filters.html', renderdict)


@staff_member_required
def my_depotlisten(request):
    return alldepots_list(request, "")


def logout_view(request):
    auth.logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("/my/home")


@staff_member_required
def short_depots_list(request):
    """
    Printable short overview list to be used when distributing
    """
    
    depots = Depot.objects.all().order_by("name")  #order_by("weekday", "code")
    numbers = Abo.objects.filter(active=True).values('groesse', 'depot').annotate(number=Count('id')).values('groesse', 'depot', 'depot__weekday', 'number')
    abo_types = Abo.abo_types.copy()
    del abo_types[Abo.SIZE_NONE]

    # todo : think fat model here...
    table = dict()
    #weekdays = dict()
    for depot in depots:
        depot_info = dict(id=depot.id, name=depot.name, weekday=depot.get_weekday_display(), sizes=dict(), total=0)
        for abo_type in abo_types:
            #print 'type', abo_type
            depot_info['sizes'][abo_type] = 0
        if depot.weekday not in table:
            table[depot.weekday] = dict()
            #weekdays[depot.weekday] = dict(name=depot.get_weekday_display(), total=0)
        table[depot.weekday][depot.id] = depot_info
            
    for number in numbers:
        print "num", number
        if not number['number']:
            #skip empty ones
            continue
        weekday = number['depot__weekday']
        depot_id = number['depot']
        groesse = number['groesse']
        number_inc = number['number'] * groesse / Abo.SIZE_SMALL
        table[weekday][depot_id]['sizes'][groesse] += number_inc
        table[weekday][depot_id]['total'] += number_inc
        #table[weekday]['total'] += number_inc
    
    print "table", table
    
    servername = request.META["SERVER_NAME"] + ':' + request.META["SERVER_PORT"]
    
    print_time = datetime.datetime.now()
    renderdict = getBohnenDict(request)
    renderdict.update({
        "abo_types": abo_types,
        "table": table,
        #"weekdays": weekdays,
        "depots": depots,
        "datum": print_time,
        "servername": servername,
    })

    #HTML Render:
    return render(request, "exports/all_depots_short.html", renderdict)
    
    #PDF Render:
    file_name = 'Depolisten_%s.pdf' % print_time.strftime("%Y%m%d_%H%M")
    return render_to_pdf(request, "exports/all_depots.html", renderdict, file_name)

@staff_member_required
def alldepots_list(request, name):
    """
    Printable list of all depots to check on get gemüse
    """
    if name == "":
        depots = Depot.objects.all().order_by("weekday", "code")
    else:
        depots = [get_object_or_404(Depot, code__iexact=name)]

    abo_types = Abo.abo_types.copy()
    print 'abo_types',abo_types
    # ignore zero-size
    del abo_types[Abo.SIZE_NONE]
    
    empty_day = {}
    for abo_type in abo_types:
        print 'abo_type', abo_type
        empty_day[abo_type] = 0
    empty_day['entities'] = 0
    
    #collect data for first page
    overview = {}
    all = empty_day.copy()    
    for depot in depots:
        weekday = depot.get_weekday_display()
        if not weekday in overview:
            overview[weekday] = empty_day.copy()
        row = overview.get(weekday)
        for abo_type in abo_types:
            number = depot.get_abo_by_size(abo_type)
            entities = number * abo_type / float(Abo.SIZE_SMALL)
            row['entities'] += entities 
            all['entities'] += entities 
            row[abo_type]   += number
            all[abo_type]   += number
    overview['all'] = all

    servername = request.META["SERVER_NAME"] + ':' + request.META["SERVER_PORT"]
    
    print_time = datetime.datetime.now()
    renderdict = {
        "abo_types": abo_types,
        "overview": overview,
        "depots": depots,
        "datum": print_time,
        "servername": servername,
    }

    #HTML Render:
    #return render(request, "exports/all_depots.html", renderdict)
    
    file_name = 'Depolisten_%s.pdf' % print_time.strftime("%Y%m%d_%H%M")
    return render_to_pdf(request, "exports/all_depots.html", renderdict, file_name)

  
@staff_member_required
def my_statistics(request):
    stat_as     = dict()
    stat_abos   = dict()
    stat_locos  = dict()
    stat_depots = dict()
    stat_jobs   = dict()

    # AS:
    stat_as['n_active'] = Anteilschein.objects.filter(canceled=False).count()
    stat_as['n_paid']   = Anteilschein.objects.filter(canceled=False, paid=True).count()
    stat_as['n_unpaid'] = stat_as['n_active'] - stat_as['n_paid']

    stat_as['perc_active'] = float(1)
    stat_as['perc_paid']   = float(stat_as['n_paid'])   / stat_as['n_active']
    stat_as['perc_unpaid'] = float(stat_as['n_unpaid']) / stat_as['n_active']

    MONEY_PER_AS = 250 # todo magic number
    stat_as['money_active'] = stat_as['n_active'] * MONEY_PER_AS
    stat_as['money_paid']   = stat_as['n_paid'] * MONEY_PER_AS
    stat_as['money_unpaid'] = stat_as['n_unpaid'] * MONEY_PER_AS 

    # Abos
    stat_abos['n_active']  = Abo.objects.filter(active=True).count()
    stat_abos['n_paid']    = Abo.objects.filter(active=True, paid=True).count()
    stat_abos['n_unpaid']  = stat_abos['n_active'] - stat_abos['n_paid']
    stat_abos['n_waiting'] = Abo.objects.filter(active=False).count()

    stat_abos['perc_active']  = float(1)
    stat_abos['perc_paid']    = float(stat_abos['n_paid'])   / stat_abos['n_active']
    stat_abos['perc_unpaid']  = float(stat_abos['n_unpaid']) / stat_abos['n_active']
    stat_abos['perc_waiting'] = float(stat_abos['n_waiting']) / stat_abos['n_active']

    stat_abos['money_active'] = 0
    stat_abos['money_paid']   = 0
    stat_abos['units_active'] = 0
    stat_abos['units_paid']   = 0
    stat_jobs['slots_available'] = 0
    stat_abos['per_size'] = []
    
    for id, the_size in Abo.abo_types.iteritems():
        the_count = Abo.objects.filter(active=True, groesse=the_size.size).count()
        the_count_paid = Abo.objects.filter(active=True, paid=True, groesse=the_size.size).count()
        size_info = (the_size.name_short, the_count)
        stat_abos['per_size'].append(size_info)
        
        stat_abos['money_active'] += the_size.cost * the_count
        stat_abos['money_paid']   += the_size.cost * the_count_paid
        
        stat_abos['units_active'] += the_size.size * the_count / Abo.SIZE_SMALL
        stat_abos['units_paid']   += the_size.size * the_count_paid / Abo.SIZE_SMALL
        
        stat_jobs['slots_available'] += the_size.required_bohnen * the_count
    stat_abos['money_unpaid'] = stat_abos['money_active'] - stat_abos['money_paid']
    stat_abos['units_unpaid'] = stat_abos['units_active'] - stat_abos['units_paid']
        
    # Locos
    stat_locos = {}
    stat_locos['n_total'] = Loco.objects.count()
    stat_locos['n_abo'] = Loco.objects.filter(abo__isnull=False).count()
    stat_locos['n_as'] = Loco.objects.annotate(num_as=Count('anteilschein')).filter(num_as__gt=0).count()
    stat_locos['n_waiting'] = Loco.objects.filter(abo__active=False).count()


    # Einsätze
    # todo limit year
    stat_jobs['offered'] = Job.objects.count()
    job_sum = Job.objects.aggregate(Sum('slots'))
    stat_jobs['slots_offered'] = job_sum['slots__sum']
    stat_jobs['slots_booked'] = Boehnli.objects.count()
    stat_jobs['slots_to_be_booked'] = stat_jobs['slots_available'] - stat_jobs['slots_booked']
    stat_jobs['slots_by_month'] = 0 #Job.objects.(Group(month))

    # Depots
    stat_depots['n_count'] = Depot.objects.count()
    stat_depots['n_abo_per_depot'] = float(stat_abos['n_active']) / stat_depots['n_count']
    #average distance to depot

    statistics = {
        'anteilsscheine': stat_as, 
        'abos':           stat_abos, 
        'locos':          stat_locos, 
        'depots':         stat_depots, 
        'jobs':           stat_jobs,
        'year':           u'2014' #todo
    };
    
    renderdict = getBohnenDict(request)
    locos = Loco.objects.select_related('abo').select_related('abo__depot').all()
    renderdict.update({
        'locos': locos,
        'statistics': statistics
    })
    return render(request, 'my_statistics.html', renderdict)
   

def my_createlocoforsuperuserifnotexist(request):
    """
    just a helper to create a loco for superuser
    """
    if request.user.is_superuser and len(Loco.objects.filter(email=request.user.email)) is 0:
        loco = Loco.objects.create(user=request.user, first_name="super", last_name="duper", email=request.user.email, addr_street="superstreet", addr_zipcode="8000",
                                   addr_location="SuperCity", phone="012345678")
        loco.save()
        request.user.loco = loco
        request.user.save()


    # we do just nothing if its not a superuser or he has already a loco
    return redirect("/my/home")

    
@staff_member_required
def my_dumpdata(request):
    if not request.user.is_superuser:
        return    
    f = StringIO()
    with Swapstd(f):
        call_command('dumpdata', indent=4)
    return HttpResponse(f.getvalue(), content_type="text/plain")

    
@staff_member_required
def my_startmigration(request):
    #TODO remove?
    return    
    f = StringIO()
    with Swapstd(f):
        pass
        #call_command('clean_db')
        #call_command('import_old_db', request.GET.get("username"), request.GET.get("password"))
    return HttpResponse(f.getvalue(), content_type="text/plain")


@staff_member_required
def migrate_apps(request):
    #TODO remove?
    return    
    f = StringIO()
    with Swapstd(f):
        call_command('migrate', 'my_ortoloco')
        call_command('migrate', 'static_ortoloco')
    return HttpResponse(f.getvalue(), content_type="text/plain")


@staff_member_required
def pip_install(request):
    #TODO remove?
    return    
    command = "pip install -r requirements.txt"
    res = run_in_shell(request, command)
    return res


def test_filters(request):
    #TODO remove?
    return    
    lst = Filter.get_all()
    res = []
    for name in Filter.get_names():
        res.append("<br><br>%s:" % name)
        tmp = Filter.execute([name], "OR")
        data = Filter.format_data(tmp, unicode)
        res.extend(data)
    return HttpResponse("<br>".join(res))


def test_filters_post(request):
    #TODO remove?
    return    
    # TODO: extract filter params from post request
    # the full list of filters is obtained by Filter.get_names()
    filters = ["Zusatzabo Eier", "Depot GZ Oerlikon"]
    op = "AND"
    res = ["Eier AND Oerlikon:<br>"]
    locos = Filter.execute(filters, op)
    data = Filter.format_data(locos, lambda loco: "%s! (email: %s)" % (loco, loco.email))
    res.extend(data)
    return HttpResponse("<br>".join(res))




