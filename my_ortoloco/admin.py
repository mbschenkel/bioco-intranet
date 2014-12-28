# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta

from django.contrib import admin, messages
from django import forms
from django.db.models import Q, F, Count, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.conf.urls import patterns
from django.utils import timezone
from django.core.urlresolvers import reverse

from my_ortoloco.models import *
from my_ortoloco import helpers
from my_ortoloco import admin_helpers

import reversion

# This form exists to restrict primary user choice to users that have actually set the
# current abo as their abo
class AboAdminForm(forms.ModelForm):
    class Meta:
        model = Abo

    abo_locos = forms.ModelMultipleChoiceField(queryset=Loco.objects.all(), required=False,
                                               widget=admin.widgets.FilteredSelectMultiple("Locos", False))

    def __init__(self, *a, **k):
        forms.ModelForm.__init__(self, *a, **k)
        self.fields["primary_loco"].queryset = Loco.objects.filter(abo=self.instance)
        self.fields["abo_locos"].queryset = Loco.objects.filter(Q(abo=None) | Q(abo=self.instance))
        self.fields["abo_locos"].initial = Loco.objects.filter(abo=self.instance)


    def clean(self):
        # enforce integrity constraint on primary_loco
        locos = self.cleaned_data["abo_locos"]
        primary = self.cleaned_data["primary_loco"]
        if primary not in locos:
            self.cleaned_data["primary_loco"] = locos[0] if locos else None

        return forms.ModelForm.clean(self)


    def save(self, commit=True):
        # HACK: set commit=True, ignoring what the admin tells us.
        # This causes save_m2m to be called.
        return forms.ModelForm.save(self, commit=True)


    def save_m2m(self):
        # update Abo-Loco many-to-one through foreign keys on Locos
        old_locos = set(Loco.objects.filter(abo=self.instance))
        new_locos = set(self.cleaned_data["abo_locos"])
        for obj in old_locos - new_locos:
            obj.abo = None
            obj.save()
        for obj in new_locos - old_locos:
            obj.abo = self.instance
            obj.save()


class JobCopyForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["typ", "slots"]

    weekdays = forms.MultipleChoiceField(label="Wochentage", choices=helpers.weekday_choices,
                                         widget=forms.widgets.CheckboxSelectMultiple)

    time = forms.TimeField(label="Zeit", required=False,
                           widget=admin.widgets.AdminTimeWidget)

    start_date = forms.DateField(label="Anfangsdatum", required=True,
                                 widget=admin.widgets.AdminDateWidget)
    end_date = forms.DateField(label="Enddatum", required=True,
                               widget=admin.widgets.AdminDateWidget)

    weekly = forms.ChoiceField(choices=[(7, "jede Woche"), (14, "Alle zwei Wochen")],
                               widget=forms.widgets.RadioSelect, initial=7)


    def __init__(self, *a, **k):
        super(JobCopyForm, self).__init__(*a, **k)
        inst = k.pop("instance")

        self.fields["start_date"].initial = inst.time.date() + datetime.timedelta(days=1)
        self.fields["time"].initial = inst.time
        self.fields["weekdays"].initial = [inst.time.isoweekday()]


    def clean(self):
        cleaned_data = forms.ModelForm.clean(self)
        if "start_date" in cleaned_data and "end_date" in cleaned_data:
            if not self.get_dates(cleaned_data):
                raise ValidationError("Kein neuer Job fällt zwischen Anfangs- und Enddatum")
        return cleaned_data


    def save(self, commit=True):
        weekdays = self.cleaned_data["weekdays"]
        start = self.cleaned_data["start_date"]
        end = self.cleaned_data["end_date"]
        time = self.cleaned_data["time"]

        inst = self.instance

        newjobs = []
        for date in self.get_dates(self.cleaned_data):
            dt = datetime.datetime.combine(date, time)
            job = Job.objects.create(typ=inst.typ, slots=inst.slots, time=dt)
            newjobs.append(job)
            job.save()

        # create new objects
        # HACK: admin expects a saveable object to be returned when commit=False
        #return newjobs[-1]
        return inst


    def save_m2m(self):
        # HACK: the admin expects this method to exist
        pass


    def get_dates(self, cleaned_data):
        start = cleaned_data["start_date"]
        end = cleaned_data["end_date"]
        weekdays = cleaned_data["weekdays"]
        weekdays = set(int(i) for i in weekdays)
        res = []
        skip_even_weeks = cleaned_data["weekly"] == "14"
        for delta in range((end - start).days + 1):
            if skip_even_weeks and delta % 14 >= 7:
                continue
            date = start + datetime.timedelta(delta)
            if not date.isoweekday() in weekdays:
                continue
            res.append(date)
        return res


class BoehnliInline(admin.TabularInline):
    model = Boehnli
    #readonly_fields = ["loco"]
    raw_id_fields = ["loco"]

    #can_delete = False

    # TODO: added these temporarily, need to be removed
    extra = 0
    max_num = 0


    def get_extra(self, request, obj=None):
        # TODO is this needed?
        #if "copy_job" in request.path:
        #    return 0
        if obj is None:
            return 0
        return obj.freie_plaetze()


    def get_max_num(self, request, obj):
        if obj is None:
            return 0
        return obj.slots


class JobFullFilter(admin.SimpleListFilter):
    title = 'Anmeldungen'
    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'booking_status'

    def lookups(self, request, model_admin):
        return (
            ('empty', u'Keine (<25%)'),
            ('half_empty', u'Wenige (<50%)'),
            ('half_full', u'Einige (>50%)'),
            ('full', u'Voll (>75%)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'empty':
            return queryset.annotate(b_count=Count('boehnli')).filter(b_count__lte=F('slots')*0.25)
        if self.value() == 'half_empty':
            return queryset.annotate(b_count=Count('boehnli')).filter(b_count__lte=F('slots')*0.5)
        if self.value() == 'half_full':
            return queryset.annotate(b_count=Count('boehnli')).filter(b_count__gte=F('slots')*0.5)
        if self.value() == 'full':
            return queryset.annotate(b_count=Count('boehnli')).filter(b_count__gte=F('slots')*0.75)
                 

class JobDateFilter(admin.SimpleListFilter):
    title = 'Zeitpunkt'
    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'job_date'

    def lookups(self, request, model_admin):
        return (
            ('past', u'Vergangene Einsätze'),
            ('last_week', u'Letzte 7 Tage'),
            ('next_week', u'Nächste 7 Tage'),
            ('future', u'Zukünftige Einsätze'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'past':
            return queryset.filter(time__lte=date.today())
        if self.value() == 'future':
            return queryset.filter(time__gte=date.today())
        if self.value() == 'last_week':
            return queryset.filter(time__lte=date.today(), 
                                   time__gte=date.today() - timedelta(days=7))
        if self.value() == 'next_week':
            return queryset.filter(time__gte=date.today(), 
                                   time__lte=date.today() + timedelta(days=7))
                                   
        
class JobAdmin(reversion.VersionAdmin):
    list_display = ["__unicode__", "typ", "time", "slots", "freie_plaetze"]
    actions = ["copy_job", "mass_copy_job"]
    search_fields = ["typ__name", "typ__bereich__name"]

    inlines = [BoehnliInline]
    readonly_fields = ["freie_plaetze"]

    list_filter = [JobFullFilter, JobDateFilter, "typ__bereich"]
    

    def mass_copy_job(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, u"Genau 1 Job auswählen!", level=messages.ERROR)
            return HttpResponseRedirect("")

        inst, = queryset.all()
        return HttpResponseRedirect("copy_job/%s/" % inst.id)

    mass_copy_job.short_description = "Job mehrfach kopieren..."


    def copy_job(self, request, queryset):
        for inst in queryset.all():
            newjob = Job(typ=inst.typ, slots=inst.slots, time=inst.time)
            newjob.save()

    copy_job.short_description = "Jobs kopieren"


    def get_form(self, request, obj=None, **kwds):
        if "copy_job" in request.path:
            return JobCopyForm
        return super(JobAdmin, self).get_form(request, obj, **kwds)


    def get_urls(self):
        urls = super(JobAdmin, self).get_urls()
        my_urls = patterns("",
                           (r"^copy_job/(?P<jobid>.*?)/$", self.admin_site.admin_view(self.copy_job_view))
        )
        return my_urls + urls


    def copy_job_view(self, request, jobid):
        # HUGE HACK: modify admin properties just for this view
        tmp_readonly = self.readonly_fields
        tmp_inlines = self.inlines
        self.readonly_fields = []
        self.inlines = []
        res = self.change_view(request, jobid, extra_context={'title': "Copy job"})
        self.readonly_fields = tmp_readonly
        self.inlines = tmp_inlines
        return res


    def construct_change_message(self, request, form, formsets):
        # As of django 1.6 the automatic logging of changes triggered by the change view behaves badly
        # when custom forms are used. This is a workaround.
        if "copy_job" in request.path:
            return ""
        return admin.ModelAdmin.construct_change_message(self, request, form, formsets)


class AboAdmin(reversion.VersionAdmin):
    form = AboAdminForm
    list_display = ["__unicode__", "active", "paid", "bezieher", "verantwortlicher_bezieher", "depot", "show_boehnli_count"]
    search_fields = ["id", "number", "locos__user__username", "locos__first_name", "locos__last_name", "depot__name"]
    list_filter = ["paid", "active"]
    
    actions = ["activate_abo", "deactivate_abo", "mark_as_paid_abo", "mark_as_unpaid_abo"]

    # Add boehnli-count per abo
    # todo limit to year if needed
    # todo this could be more efficient...
    def show_boehnli_count(self, inst):
        abo_id = inst.pk
        locos = Loco.objects.filter(abo=abo_id);
        cnt = 0
        for loco in locos:
            cnt += loco.boehnli_set.count()
        return cnt
    show_boehnli_count.short_description = 'Anzahl Einsätze'

    def activate_abo(self, request, queryset):
        queryset.update(active=True)
    def deactivate_abo(self, request, queryset):
        queryset.update(active=False)
    
    activate_abo.short_description = "Abos auf aktiv schalten"
    deactivate_abo.short_description = "Abos auf inaktiv schalten"
    
    def mark_as_paid_abo(self, request, queryset):
        queryset.update(paid=True)
    def mark_as_unpaid_abo(self, request, queryset):
        queryset.update(paid=False)
    
    mark_as_paid_abo.short_description = "Abos als bezahlt markieren"
    mark_as_unpaid_abo.short_description = "Abos als nicht bezahlt markieren"

    
class AuditAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "source_type", "target_type", "field", "action",
                    "source_object", "target_object"]
    #can_delete = False


class AnteilscheinAdmin(reversion.VersionAdmin):
    list_display = ["__unicode__", "canceled", "paid", "loco"]
    list_filter = ["paid", "canceled"]
    search_fields = ["id", "number", "loco__email", "loco__first_name", "loco__last_name"]
    raw_id_fields = ["loco"]
    actions = ["mark_as_paid_anteilsschein", "mark_as_unpaid_anteilsschein"]

    def mark_as_paid_anteilsschein(self, request, queryset):
        queryset.update(paid=True)
    def mark_as_unpaid_anteilsschein(self, request, queryset):
        queryset.update(paid=False)
    
    mark_as_paid_anteilsschein.short_description = "Anteilsscheine als bezahlt markieren"
    mark_as_unpaid_anteilsschein.short_description = "Anteilsscheine als nicht bezahlt markieren"


class DepotAdmin(reversion.VersionAdmin):
    raw_id_fields = ["contact"]
    list_display = ["name", "code", "weekday", "contact"]


class BereichAdmin(reversion.VersionAdmin):
    filter_horizontal = ["locos"]
    raw_id_fields = ["coordinator"]
    list_display = ["name", "core", "hidden", "coordinator", "show_loco_count"]

    def queryset(self, request):
        return Taetigkeitsbereich.objects.annotate(loco_count=Count('locos'))
    def show_loco_count(self, inst):
        return inst.loco_count
    show_loco_count.admin_order_field = 'loco_count'
    show_loco_count.short_description = 'Anzahl Mitglieder'
    
    
class BoehnliDateFilter(admin.SimpleListFilter):
    title = 'Zeitpunkt'
    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'boehnli_date'

    def lookups(self, request, model_admin):
        return (
            ('past', u'Vergangene Einsätze'),
            ('last_week', u'Letzte 7 Tage'),
            ('next_week', u'Nächste 7 Tage'),
            ('future', u'Zukünftige Einsätze'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'past':
            return queryset.filter(job__time__lte=date.today())
        if self.value() == 'future':
            return queryset.filter(job__time__gte=date.today())
        if self.value() == 'last_week':
            return queryset.filter(job__time__lte=date.today(), 
                                   job__time__gte=date.today() - timedelta(days=7))
        if self.value() == 'next_week':
            return queryset.filter(job__time__gte=date.today(), 
                                   job__time__lte=date.today() + timedelta(days=7))
                                    
class BoehnliCarFilter(admin.SimpleListFilter):
    title = 'Auto'
    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'boehnli_car'

    def lookups(self, request, model_admin):
        return (
            ('not_needed', u'Nicht benötigt'),
            ('needed_available', u'Benötigt und verfügbar'),
            ('needed_not_available', u'Benötigt aber nicht verfügbar'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'not_needed':
            return queryset.filter(job__typ__car_needed=False)
        if self.value() == 'needed_available':
            return queryset.filter(job__typ__car_needed=True, with_car=True)
        if self.value() == 'needed_not_available':
            return queryset.filter(job__typ__car_needed=True, with_car=False)

class BoehnliAdmin(reversion.VersionAdmin):
    def job_with_name(self, obj):
        return obj.job.name
    def car_needed(self, obj):
        return obj.job.typ.car_needed
    # show pretty icon
    car_needed.boolean = True
    
    list_display = ["__unicode__", "job_link", "zeit", "loco_link", "car_needed", "with_car"]
    search_fields = ["id", "job__typ__name", "job__typ__displayed_name", "loco__user__username", "loco__first_name", "loco__last_name"]
    list_filter = [BoehnliCarFilter, BoehnliDateFilter]
    raw_id_fields = ["job", "loco"]
    
    def job_link(self, obj):
        return u'<a href="/admin/my_ortoloco/job/%s/">%s</a>' % (obj.job.pk, obj.job)
        
    def loco_link(self, obj):
        return u'<a href="/admin/my_ortoloco/loco/%s/">%s</a>' % (obj.loco.pk, obj.loco)
        
    # Not recommended to edit Boehnli directly, thus only showing the link to the job (and loco)
    job_link.allow_tags = True
    job_link.short_description = "Job"
    loco_link.allow_tags = True
    loco_link.short_description = "Mitglied"
    
    # In django 1.7 there'd be a valid
    # list_display_links = None
    def __init__(self,*args,**kwargs):
        super(BoehnliAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )
        

class LocoAdminForm(forms.ModelForm):
    class Meta:
        model = Loco


    def __init__(self, *a, **k):
        forms.ModelForm.__init__(self, *a, **k)
        loco = k.get("instance")
        if loco is None:
            link = ""
        elif loco.abo:
            url = reverse("admin:my_ortoloco_abo_change", args=(loco.abo.id,))
            link = "<a href=%s>%s</a>" % (url, loco.abo)
        else:
            link = "Kein Abo"
        self.fields["abo_link"].initial = link

    abo_link = forms.URLField(widget=admin_helpers.MyHTMLWidget(), required=False,
                              label="Abo")


class LocoAdmin(reversion.VersionAdmin):
    form = LocoAdminForm
    list_display = ["email", "sex", "first_name", "last_name", "show_boehnli_count", "abo_size"]
    search_fields = ["first_name", "last_name", "email"]
    #raw_id_fields = ["abo"]
    exclude = ["abo"]
    readonly_fields = ["user"]
    actions = ["impersonate_job"]

    list_filter = ["addr_location", "sex", "abo__groesse"] 
    
    # Add boehnli-count to SQL query as a left-join
    def queryset(self, request):
        # todo limit to year, might need https://pypi.python.org/pypi/django-aggregate-if/
        return Loco.objects.annotate(boehnli_count=Count('boehnli'))
    def show_boehnli_count(self, inst):
        return inst.boehnli_count
    show_boehnli_count.admin_order_field = 'boehnli_count'
    show_boehnli_count.short_description = 'Anzahl Einsätze'

    # Show abo
    def abo_size(self, inst):
        abo = inst.abo
        if abo:
            size = abo.groesse
            return Abo.abo_types[size].name_long
        else:
            return 'Kein Abo'
    abo_size.admin_order_field = "abo__groesse"
    abo_size.short_description = 'Abo'
    
    def impersonate_job(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, u"Genau 1 Loco auswählen!", level=messages.ERROR)
            return HttpResponseRedirect("")
        inst, = queryset.all()
        return HttpResponseRedirect("/impersonate/%s/" % inst.user.id)
    impersonate_job.short_description = "Loco imitieren (impersonate)..."

class JobTypAdmin(reversion.VersionAdmin):
    list_display = ["name", "displayed_name", "bereich", "location", "duration", "car_needed" ]
    search_fields = ["name", "displayed_name", "bereich", "location"]
    
class JobCommentAdmin(reversion.VersionAdmin):
    list_display = ["job", "loco", "time", "text" ]
    list_filter = ["loco"]
    search_fields = ["job", "loco", "text"]
    

admin.site.register(Depot, DepotAdmin)
admin.site.register(ExtraAboType)
admin.site.register(Abo, AboAdmin)
admin.site.register(Loco, LocoAdmin)
admin.site.register(Taetigkeitsbereich, BereichAdmin)
admin.site.register(Anteilschein, AnteilscheinAdmin)

# This is only added to admin for debugging
# admin.site.register(model_audit.Audit, AuditAdmin)

# Adding this without edit-links, because it can and should be edited 
# from Job, where integrity constraints are checked
admin.site.register(Boehnli, BoehnliAdmin)
admin.site.register(JobTyp, JobTypAdmin)
admin.site.register(JobComment, JobCommentAdmin)
admin.site.register(Job, JobAdmin)
