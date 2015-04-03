from functools import wraps
from django.shortcuts import get_object_or_404
from my_ortoloco.models import Abo
from django.http import HttpResponseRedirect

def login_of_active_loco_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user  
        loco = user.loco
        
        print "login_of_active_loco_required", loco
        
        if request.user.is_authenticated():
            if loco.confirmed and user.is_active:
                return view(request, *args, **kwargs)
            else:
                # user is logged in but not active and is not supposed to see a page 
                # -> forward to home page where we show a hint
                return HttpResponseRedirect("/")
        else:
            return HttpResponseRedirect("/accounts/login/?next=" + str(request.get_full_path()))

    return wrapper

def primary_loco_of_abo(view):
    @wraps(view)
    def wrapper(request, abo_id, *args, **kwargs):
        if request.user.is_authenticated():
            abo = get_object_or_404(Abo, id=abo_id)
            if abo.primary_loco.id == request.user.loco.id:
                return view(request, abo_id=abo_id, *args, **kwargs)
            else:
                return HttpResponseRedirect("/accounts/login/?next=" + str(request.get_full_path()))
        else:
            return HttpResponseRedirect("/accounts/login/?next=" + str(request.get_full_path()))

    return wrapper
