import os
import io
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from .models import (
    Reporter, Desk, SocialMedia, GraphicDesigner, InputUser, VoiceOverUser, CopyEditor, VisualEditor, generate_next_reporter_id,
    News, NewsMedia, NEWS_TYPE_CHOICES, NEWS_CATEGORY_CHOICES, NEWS_STATUS_CHOICES, TeleprompterScript, DeskVisualChatMessage, DeskCopyChatMessage, DeskVoiceOverChatMessage, DeskSocialChatMessage, DeskReporterChatMessage,
    MediaDownloadRequest, LiveStreamSetting, LiveBroadcastSession
)


# ==========================================
# Custom Auth & Role Helpers
# ==========================================
def get_base_template(user):
    if hasattr(user, 'reporter_profile'):
        return 'reporter/base_reporter.html'
    elif hasattr(user, 'desk_profile'):
        return 'desk/base_desk.html'
    elif hasattr(user, 'social_media_profile'):
        return 'social_media/base_social_media.html'
    elif hasattr(user, 'graphic_designer_profile'):
        return 'graphic_designer/base_graphic_designer.html'
    elif hasattr(user, 'input_profile'):
        return 'input/base_input.html'
    elif hasattr(user, 'voice_over_profile'):
        return 'voice_over/base_voice_over.html'
    elif hasattr(user, 'copy_editor_profile'):
        return 'copy_editor/base_copy_editor.html'
    elif hasattr(user, 'visual_editor_profile'):
        return 'visual_editor/base_visual_editor.html'
    return 'base.html'


def is_reporter_user(user):
    return user.is_authenticated and hasattr(user, 'reporter_profile')


def is_desk_user(user):
    return user.is_authenticated and hasattr(user, 'desk_profile')


def is_social_media_user(user):
    return user.is_authenticated and hasattr(user, 'social_media_profile')


def is_graphic_designer_user(user):
    return user.is_authenticated and hasattr(user, 'graphic_designer_profile')


def is_input_user(user):
    return user.is_authenticated and hasattr(user, 'input_profile')


def is_voice_over_user(user):
    return user.is_authenticated and hasattr(user, 'voice_over_profile')


def is_copy_editor_user(user):
    return user.is_authenticated and hasattr(user, 'copy_editor_profile')


def is_visual_editor_user(user):
    return user.is_authenticated and hasattr(user, 'visual_editor_profile')


def is_admin_user(user):
    return (
        user.is_authenticated and
        not hasattr(user, 'reporter_profile') and
        not hasattr(user, 'desk_profile') and
        not hasattr(user, 'social_media_profile') and
        not hasattr(user, 'graphic_designer_profile') and
        not hasattr(user, 'input_profile') and
        not hasattr(user, 'voice_over_profile') and
        not hasattr(user, 'copy_editor_profile') and
        not hasattr(user, 'visual_editor_profile')
    )


def is_live_control_authorized(user):
    if not (user and user.is_authenticated):
        return False
    return (
        hasattr(user, 'social_media_profile') or
        hasattr(user, 'desk_profile') or
        user.is_superuser or
        user.is_staff or
        is_admin_user(user)
    )



def admin_required(view_func):
    """
    Decorator ensuring only Admin users can access the view.
    Reporters, Desk, Social Media, Graphic Designers, Input, Voice Over, Copy Editor, and Visual Editor staff are redirected to their respective dashboards.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def reporter_required(view_func):
    """
    Decorator ensuring only Reporter users can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_reporter_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def desk_required(view_func):
    """
    Decorator ensuring only Desk users can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_desk_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def social_media_required(view_func):
    """
    Decorator ensuring only Social Media staff can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_social_media_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def graphic_designer_required(view_func):
    """
    Decorator ensuring only Graphic Designer staff can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_graphic_designer_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def input_required(view_func):
    """
    Decorator ensuring only Input staff can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_input_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def voice_over_required(view_func):
    """
    Decorator ensuring only Voice Over staff can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_voice_over_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def copy_editor_required(view_func):
    """
    Decorator ensuring only Copy Editor staff can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        if not is_copy_editor_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def visual_editor_required(view_func):
    """
    Decorator ensuring only Visual Editor staff can access the view.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_home')
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if not is_visual_editor_user(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view




# ==========================================
# Authentication Presence Helpers
# ==========================================
def mark_login_presence(request, user):
    """
    Updates last_login and immediately marks the user's role profile Online.
    """
    now = timezone.now()
    try:
        from .models import EXPLICITLY_LOGGED_OUT, _ACTIVE_USERS_CACHE
        EXPLICITLY_LOGGED_OUT.pop(user.pk, None)
        _ACTIVE_USERS_CACHE['timestamp'] = 0
    except Exception:
        pass
    if request:
        try:
            request.session['last_seen_ping'] = now.timestamp()
        except Exception:
            pass
    try:
        user.last_login = now
        user.save(update_fields=['last_login'])
    except Exception:
        pass
    from .middleware import touch_user_last_seen
    touch_user_last_seen(user, now)


def mark_logout_presence(request):
    """
    Immediately marks the logging out user as Offline with accurate last seen time.
    """
    u = getattr(request, 'user', None)
    if u and u.is_authenticated:
        now = timezone.now()
        from .middleware import touch_user_last_seen
        touch_user_last_seen(u, now)
        try:
            from .models import EXPLICITLY_LOGGED_OUT, _ACTIVE_USERS_CACHE
            EXPLICITLY_LOGGED_OUT[u.pk] = now
            _ACTIVE_USERS_CACHE['timestamp'] = 0
        except Exception:
            pass
    logout(request)


# ==========================================
# Authentication Views (Admin + Reporter + Desk)
# ==========================================
def login_view(request):
    """
    Multi-Role Login View:
    1. Admin Login (Email/Username + Password)
    2. Reporter Login (Phone Number + Password)
    3. Desk Login (Phone Number + Password)
    4. Social Media Login (Phone Number + Password)
    5. Graphic Designer Login (Phone Number + Password)
    6. Input Login (Phone Number + Password)
    7. Voice Over Login (Phone Number + Password)
    8. Copy Editor Login (Phone Number + Password)
    """
    if request.user.is_authenticated:
        mark_login_presence(request, request.user)
        if is_reporter_user(request.user):
            return redirect('reporter_dashboard')
        if is_desk_user(request.user):
            return redirect('desk_dashboard')
        if is_social_media_user(request.user):
            return redirect('social_media_dashboard')
        if is_graphic_designer_user(request.user):
            return redirect('graphic_designer_dashboard')
        if is_input_user(request.user):
            return redirect('input_dashboard')
        if is_voice_over_user(request.user):
            return redirect('voice_over_dashboard')
        if is_copy_editor_user(request.user):
            return redirect('copy_editor_dashboard')
        if is_visual_editor_user(request.user):
            return redirect('visual_editor_dashboard')
        return redirect('dashboard')

    active_tab = request.GET.get('tab', 'admin')
    admin_error = None
    reporter_error = None
    desk_error = None
    social_media_error = None
    graphic_designer_error = None
    input_error = None
    voice_over_error = None
    copy_editor_error = None
    visual_editor_error = None

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'admin').strip()
        active_tab = login_type

        if login_type == 'admin':
            email_or_username = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')

            if not email_or_username or not password:
                admin_error = "Please enter both Email/Username and Password."
            else:
                # Lookup user by email or username
                matched_user = User.objects.filter(email__iexact=email_or_username).first()
                if not matched_user:
                    matched_user = User.objects.filter(username__iexact=email_or_username).first()

                user = None
                if matched_user:
                    # Prevent other portal roles from logging in via admin tab
                    if hasattr(matched_user, 'reporter_profile'):
                        admin_error = "This is a Reporter account. Please use the Reporter Login tab."
                    elif hasattr(matched_user, 'desk_profile'):
                        admin_error = "This is a Desk account. Please use the Desk Login tab."
                    elif hasattr(matched_user, 'social_media_profile'):
                        admin_error = "This is a Social Media account. Please use the Social Media Login tab."
                    elif hasattr(matched_user, 'graphic_designer_profile'):
                        admin_error = "This is a Graphic Designer account. Please use the Designer Login tab."
                    elif hasattr(matched_user, 'input_profile'):
                        admin_error = "This is an Input account. Please use the Input Login tab."
                    elif hasattr(matched_user, 'voice_over_profile'):
                        admin_error = "This is a Voice Over account. Please use the Voice Over Login tab."
                    elif hasattr(matched_user, 'copy_editor_profile'):
                        admin_error = "This is a Copy Editor account. Please use the Copy Editor Login tab."
                    elif hasattr(matched_user, 'visual_editor_profile'):
                        admin_error = "This is a Visual Editor account. Please use the Visual Editor Login tab."
                    else:
                        user = authenticate(request, username=matched_user.username, password=password)
                else:
                    user = authenticate(request, username=email_or_username, password=password)

                if user is not None:
                    if user.is_active:
                        login(request, user)
                        mark_login_presence(request, user)
                        next_url = request.GET.get('next')
                        if next_url and next_url != '/':
                            return redirect(next_url)
                        return redirect('dashboard')
                    else:
                        admin_error = "This admin account has been disabled."
                elif not admin_error:
                    admin_error = "Invalid Admin credentials. Please try again."

        elif login_type == 'reporter':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                reporter_error = "Please enter both Phone Number/Reporter ID and Password."
            else:
                reporter = Reporter.objects.filter(
                    Q(phone_number=phone) | Q(reporter_id__iexact=phone)
                ).first()
                if not reporter:
                    reporter_error = "No Reporter account found with this Phone Number or Reporter ID."
                elif not reporter.is_active:
                    reporter_error = "Your Reporter account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=reporter.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('reporter_dashboard')
                        else:
                            reporter_error = "This Reporter user account has been disabled."
                    else:
                        reporter_error = "Incorrect Password. Please check and try again."

        elif login_type == 'desk':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                desk_error = "Please enter both Phone Number and Password."
            else:
                desk = Desk.objects.filter(phone_number=phone).first()
                if not desk:
                    desk = Desk.objects.filter(email__iexact=phone).first()

                if not desk:
                    desk_error = "No Desk account found with this Phone Number."
                elif not desk.is_active:
                    desk_error = "Your Desk account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=desk.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('desk_dashboard')
                        else:
                            desk_error = "This Desk user account has been disabled."
                    else:
                        desk_error = "Incorrect Password. Please check and try again."

        elif login_type == 'social_media':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                social_media_error = "Please enter both Phone Number and Password."
            else:
                sm_user = SocialMedia.objects.filter(phone_number=phone).first()
                if not sm_user:
                    social_media_error = "No Social Media account found with this Phone Number."
                elif not sm_user.is_active:
                    social_media_error = "Your Social Media account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=sm_user.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('social_media_dashboard')
                        else:
                            social_media_error = "This Social Media account has been disabled."
                    else:
                        social_media_error = "Incorrect Password. Please check and try again."

        elif login_type == 'graphic_designer':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                graphic_designer_error = "Please enter both Phone Number and Password."
            else:
                gd_user = GraphicDesigner.objects.filter(phone_number=phone).first()
                if not gd_user:
                    graphic_designer_error = "No Graphic Designer account found with this Phone Number."
                elif not gd_user.is_active:
                    graphic_designer_error = "Your Graphic Designer account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=gd_user.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('graphic_designer_dashboard')
                        else:
                            graphic_designer_error = "This Graphic Designer account has been disabled."
                    else:
                        graphic_designer_error = "Incorrect Password. Please check and try again."

        elif login_type == 'input':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                input_error = "Please enter both Phone Number and Password."
            else:
                input_user = InputUser.objects.filter(phone_number=phone).first()
                if not input_user:
                    input_error = "No Input account found with this Phone Number."
                elif not input_user.is_active:
                    input_error = "Your Input account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=input_user.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('input_dashboard')
                        else:
                            input_error = "This Input account has been disabled."
                    else:
                        input_error = "Incorrect Password. Please check and try again."

        elif login_type == 'voice_over':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                voice_over_error = "Please enter both Phone Number and Password."
            else:
                vo_user = VoiceOverUser.objects.filter(phone_number=phone).first()
                if not vo_user:
                    voice_over_error = "No Voice Over account found with this Phone Number."
                elif not vo_user.is_active:
                    voice_over_error = "Your Voice Over account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=vo_user.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('voice_over_dashboard')
                        else:
                            voice_over_error = "This Voice Over account has been disabled."
                    else:
                        voice_over_error = "Incorrect Password. Please check and try again."

        elif login_type == 'copy_editor':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                copy_editor_error = "Please enter both Phone Number and Password."
            else:
                ce_user = CopyEditor.objects.filter(phone_number=phone).first()
                if not ce_user:
                    copy_editor_error = "No Copy Editor account found with this Phone Number."
                elif not ce_user.is_active:
                    copy_editor_error = "Your Copy Editor account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=ce_user.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('copy_editor_dashboard')
                        else:
                            copy_editor_error = "This Copy Editor account has been disabled."
                    else:
                        copy_editor_error = "Incorrect Password. Please check and try again."

        elif login_type == 'visual_editor':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '')

            if not phone or not password:
                visual_editor_error = "Please enter both Phone Number and Password."
            else:
                ve_user = VisualEditor.objects.filter(phone_number=phone).first()
                if not ve_user:
                    visual_editor_error = "No Visual Editor account found with this Phone Number."
                elif not ve_user.is_active:
                    visual_editor_error = "Your Visual Editor account is currently inactive. Contact Admin."
                else:
                    user = authenticate(request, username=ve_user.user.username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            mark_login_presence(request, user)
                            return redirect('visual_editor_dashboard')
                        else:
                            visual_editor_error = "This Visual Editor account has been disabled."
                    else:
                        visual_editor_error = "Incorrect Password. Please check and try again."

    return render(request, 'login.html', {
        'active_tab': active_tab,
        'admin_error': admin_error,
        'reporter_error': reporter_error,
        'desk_error': desk_error,
        'social_media_error': social_media_error,
        'graphic_designer_error': graphic_designer_error,
        'input_error': input_error,
        'voice_over_error': voice_over_error,
        'copy_editor_error': copy_editor_error,
        'visual_editor_error': visual_editor_error,
    })


def logout_view(request):
    """
    Logs out user and redirects to login.
    """
    mark_logout_presence(request)
    return redirect('login_home')


def reporter_logout_view(request):
    """
    Logs out reporter and redirects to login with reporter tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=reporter')


def desk_logout_view(request):
    """
    Logs out desk staff and redirects to login with desk tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=desk')


def social_media_logout_view(request):
    """
    Logs out social media staff and redirects to login with social_media tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=social_media')


def graphic_designer_logout_view(request):
    """
    Logs out graphic designer and redirects to login with graphic_designer tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=graphic_designer')


def input_logout_view(request):
    """
    Logs out input staff and redirects to login with input tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=input')


def voice_over_logout_view(request):
    """
    Logs out voice over staff and redirects to login with voice_over tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=voice_over')


def copy_editor_logout_view(request):
    """
    Logs out copy editor staff and redirects to login with copy_editor tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=copy_editor')


def visual_editor_logout_view(request):
    """
    Logs out visual editor staff and redirects to login with visual_editor tab active.
    """
    mark_logout_presence(request)
    return redirect('/?tab=visual_editor')


@login_required
def heartbeat_api(request):
    """
    Lightweight background heartbeat ping for active browser sessions.
    Keeps user marked Online while working on any portal page.
    """
    now = timezone.now()
    from .middleware import touch_user_last_seen
    touch_user_last_seen(request.user, now)
    return JsonResponse({'status': 'ok'})




# ==========================================
# Admin Control Panel - Dashboard & Profile
# ==========================================
@admin_required
def dashboard_view(request):
    """
    Admin Dashboard with Reporter, Desk, Social Media, Graphic Designer, Input, Voice Over & Copy Editor metrics and quick overview.
    """
    total_reporters = Reporter.objects.count()
    active_reporters = Reporter.objects.filter(is_active=True).count()
    districts_count = Reporter.objects.values('district').distinct().count()
    recent_reporters = Reporter.objects.all()[:6]

    total_desks = Desk.objects.count()
    active_desks = Desk.objects.filter(is_active=True).count()
    recent_desks = Desk.objects.all()[:6]

    total_social_media = SocialMedia.objects.count()
    active_social_media = SocialMedia.objects.filter(is_active=True).count()
    recent_social_media = SocialMedia.objects.all()[:6]

    total_graphic_designers = GraphicDesigner.objects.count()
    active_graphic_designers = GraphicDesigner.objects.filter(is_active=True).count()
    recent_graphic_designers = GraphicDesigner.objects.all()[:6]

    total_inputs = InputUser.objects.count()
    active_inputs = InputUser.objects.filter(is_active=True).count()
    recent_inputs = InputUser.objects.all()[:6]

    total_voice_overs = VoiceOverUser.objects.count()
    active_voice_overs = VoiceOverUser.objects.filter(is_active=True).count()
    recent_voice_overs = VoiceOverUser.objects.all()[:6]

    total_copy_editors = CopyEditor.objects.count()
    active_copy_editors = CopyEditor.objects.filter(is_active=True).count()
    recent_copy_editors = CopyEditor.objects.all()[:6]

    total_visual_editors = VisualEditor.objects.count()
    active_visual_editors = VisualEditor.objects.filter(is_active=True).count()
    recent_visual_editors = VisualEditor.objects.all()[:6]

    total_news = News.objects.count()
    recent_news = News.objects.select_related('reporter', 'author').order_by('-created_at')[:6]

    context = {
        'active_page': 'dashboard',
        'total_reporters': total_reporters,
        'active_reporters': active_reporters,
        'districts_count': districts_count,
        'recent_reporters': recent_reporters,
        'total_desks': total_desks,
        'active_desks': active_desks,
        'recent_desks': recent_desks,
        'total_social_media': total_social_media,
        'active_social_media': active_social_media,
        'recent_social_media': recent_social_media,
        'total_graphic_designers': total_graphic_designers,
        'active_graphic_designers': active_graphic_designers,
        'recent_graphic_designers': recent_graphic_designers,
        'total_inputs': total_inputs,
        'active_inputs': active_inputs,
        'recent_inputs': recent_inputs,
        'total_voice_overs': total_voice_overs,
        'active_voice_overs': active_voice_overs,
        'recent_voice_overs': recent_voice_overs,
        'total_copy_editors': total_copy_editors,
        'active_copy_editors': active_copy_editors,
        'recent_copy_editors': recent_copy_editors,
        'total_visual_editors': total_visual_editors,
        'active_visual_editors': active_visual_editors,
        'recent_visual_editors': recent_visual_editors,
        'total_news': total_news,
        'recent_news': recent_news,
    }
    return render(request, 'dashboard.html', context)



@admin_required
def profile_view(request):
    """
    Admin Profile page.
    """
    context = {
        'active_page': 'profile',
        'admin_user': request.user,
        'total_reporters': Reporter.objects.count(),
        'total_desks': Desk.objects.count(),
        'total_social_media': SocialMedia.objects.count(),
        'total_graphic_designers': GraphicDesigner.objects.count(),
        'total_inputs': InputUser.objects.count(),
        'total_voice_overs': VoiceOverUser.objects.count(),
        'total_copy_editors': CopyEditor.objects.count(),
        'total_visual_editors': VisualEditor.objects.count(),
    }
    return render(request, 'profile.html', context)


# ==========================================
# Reporter Management Views (Admin Control)
# ==========================================
@admin_required
def reporter_list_view(request):
    """
    Reporter List with search, district filter, and management table.
    """
    query = request.GET.get('q', '').strip()
    district_filter = request.GET.get('district', '').strip()
    status_filter = request.GET.get('status', '').strip()

    reporters = Reporter.objects.all()

    if query:
        reporters = reporters.filter(
            Q(reporter_id__icontains=query) |
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(district__icontains=query) |
            Q(address__icontains=query)
        )

    if district_filter:
        reporters = reporters.filter(district__iexact=district_filter)

    if status_filter == 'active':
        reporters = reporters.filter(is_active=True)
    elif status_filter == 'inactive':
        reporters = reporters.filter(is_active=False)

    all_districts = Reporter.objects.values_list('district', flat=True).distinct().order_by('district')

    context = {
        'active_page': 'reporter_list',
        'reporters': reporters,
        'all_districts': all_districts,
        'query': query,
        'district_filter': district_filter,
        'status_filter': status_filter,
    }
    return render(request, 'admin/reporter_list.html', context)


@admin_required
def reporter_add_view(request):
    """
    Add New Reporter form.
    Fields: Name, Address, Phone Number, Dist Name, Reporter ID (auto/custom), Aadhar Card image, Profile image, Password & Confirm Password.
    """
    errors = {}
    form_data = {}
    next_reporter_id = generate_next_reporter_id()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        district = request.POST.get('district', '').strip()
        reporter_id = request.POST.get('reporter_id', '').strip() or next_reporter_id
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        aadhar_image = request.FILES.get('aadhar_image')
        profile_image = request.FILES.get('profile_image')

        form_data = {
            'name': name,
            'address': address,
            'phone_number': phone_number,
            'district': district,
            'reporter_id': reporter_id,
        }

        # Validation
        if not name:
            errors['name'] = "Reporter Name is required."
        if not address:
            errors['address'] = "Address is required."
        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif Reporter.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "A Reporter or User with this Phone Number already exists."
        if not district:
            errors['district'] = "District Name is required."
        if reporter_id and Reporter.objects.filter(reporter_id__iexact=reporter_id).exists():
            errors['reporter_id'] = f"Reporter ID '{reporter_id}' is already registered."
        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password should be at least 4 characters long."
        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create Reporter Profile
            reporter = Reporter(
                user=user,
                reporter_id=reporter_id,
                name=name,
                phone_number=phone_number,
                address=address,
                district=district,
                is_active=True
            )
            if aadhar_image:
                reporter.aadhar_image = aadhar_image
            if profile_image:
                reporter.profile_image = profile_image

            reporter.save()

            messages.success(request, f'Reporter "{reporter.name}" has been registered successfully with ID: {reporter.reporter_id}!')
            return redirect('reporter_list')

    context = {
        'active_page': 'reporter_add',
        'errors': errors,
        'form_data': form_data,
        'next_reporter_id': next_reporter_id,
    }
    return render(request, 'admin/reporter_add.html', context)


@admin_required
def reporter_detail_view(request, pk):
    """
    View Reporter full details / ID card / documents.
    """
    reporter = get_object_or_404(Reporter, pk=pk)
    context = {
        'active_page': 'reporter_list',
        'reporter': reporter,
    }
    return render(request, 'admin/reporter_view.html', context)


@admin_required
def reporter_edit_view(request, pk):
    """
    Edit existing Reporter information.
    """
    reporter = get_object_or_404(Reporter, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        district = request.POST.get('district', '').strip()
        reporter_id = request.POST.get('reporter_id', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        profile_image = request.FILES.get('profile_image')
        aadhar_image = request.FILES.get('aadhar_image')
        remove_profile = request.POST.get('remove_profile') == '1'
        remove_aadhar = request.POST.get('remove_aadhar') == '1'

        if not name:
            errors['name'] = "Name is required."
        if not address:
            errors['address'] = "Address is required."
        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif Reporter.objects.filter(phone_number=phone_number).exclude(pk=reporter.pk).exists():
            errors['phone_number'] = "Another Reporter with this phone number already exists."
        if not district:
            errors['district'] = "District Name is required."
        if reporter_id and Reporter.objects.filter(reporter_id__iexact=reporter_id).exclude(pk=reporter.pk).exists():
            errors['reporter_id'] = f"Another Reporter with ID '{reporter_id}' already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            reporter.name = name
            if reporter_id:
                reporter.reporter_id = reporter_id
            reporter.address = address
            reporter.district = district
            reporter.is_active = is_active

            # Update User username if phone changed
            user = reporter.user
            user.first_name = name
            if phone_number != reporter.phone_number:
                reporter.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.is_active = is_active
            user.save()

            if remove_profile and reporter.profile_image:
                reporter.profile_image.delete(save=False)
                reporter.profile_image = None
            elif profile_image:
                reporter.profile_image = profile_image

            if remove_aadhar and reporter.aadhar_image:
                reporter.aadhar_image.delete(save=False)
                reporter.aadhar_image = None
            elif aadhar_image:
                reporter.aadhar_image = aadhar_image

            reporter.save()
            messages.success(request, f'Reporter "{reporter.name}" was updated successfully.')
            return redirect('reporter_list')

    context = {
        'active_page': 'reporter_list',
        'reporter': reporter,
        'errors': errors,
    }
    return render(request, 'admin/reporter_edit.html', context)


@admin_required
def reporter_delete_view(request, pk):
    """
    Delete Reporter and linked auth User.
    """
    reporter = get_object_or_404(Reporter, pk=pk)
    name = reporter.name
    
    # Delete images
    if reporter.profile_image:
        reporter.profile_image.delete(save=False)
    if reporter.aadhar_image:
        reporter.aadhar_image.delete(save=False)
    
    # Deleting user will cascade delete reporter
    user = reporter.user
    user.delete()

    messages.success(request, f'Reporter "{name}" has been deleted successfully.')
    return redirect('reporter_list')


# ==========================================
# Desk Management Views (Admin Control)
# ==========================================
@admin_required
def desk_list_view(request):
    """
    Desk Staff List with search, status filtering, and management actions (View, Edit, Delete).
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    desks = Desk.objects.all()

    if query:
        desks = desks.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(email__icontains=query)
        )

    if status_filter == 'active':
        desks = desks.filter(is_active=True)
    elif status_filter == 'inactive':
        desks = desks.filter(is_active=False)

    context = {
        'active_page': 'desk_list',
        'desks': desks,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'admin/desk_list.html', context)


@admin_required
def desk_add_view(request):
    """
    Add New Desk Staff form.
    Fields: Name, Phone number, Gmail ID, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
            'email': email,
        }

        # Validation
        if not name:
            errors['name'] = "Desk Staff Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif Desk.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not email:
            errors['email'] = "Gmail / Email ID is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = "Please enter a valid email address (e.g. example@gmail.com)."

            if not errors.get('email') and (Desk.objects.filter(email__iexact=email).exists() or User.objects.filter(email__iexact=email).exists()):
                errors['email'] = "An account with this Email ID already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                email=email,
                first_name=name,
                password=password
            )

            # 2. Create Desk Profile
            desk = Desk.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                email=email,
                is_active=True
            )

            messages.success(request, f'Desk user "{desk.name}" registered successfully!')
            return redirect('desk_list')

    context = {
        'active_page': 'desk_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/desk_add.html', context)


@admin_required
def desk_detail_view(request, pk):
    """
    View Desk full details / ID card.
    """
    desk = get_object_or_404(Desk, pk=pk)
    context = {
        'active_page': 'desk_list',
        'desk': desk,
    }
    return render(request, 'admin/desk_view.html', context)


@admin_required
def desk_edit_view(request, pk):
    """
    Edit existing Desk user information.
    """
    desk = get_object_or_404(Desk, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif Desk.objects.filter(phone_number=phone_number).exclude(pk=desk.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=desk.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if not email:
            errors['email'] = "Email ID is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = "Please enter a valid email address."

            if not errors.get('email') and (
                Desk.objects.filter(email__iexact=email).exclude(pk=desk.pk).exists() or
                User.objects.filter(email__iexact=email).exclude(pk=desk.user.pk).exists()
            ):
                errors['email'] = "Another account with this Email ID already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            desk.name = name
            desk.email = email
            desk.is_active = is_active

            # Update linked Auth User
            user = desk.user
            user.first_name = name
            user.email = email
            user.is_active = is_active

            if phone_number != desk.phone_number:
                desk.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            desk.save()

            messages.success(request, f'Desk user "{desk.name}" updated successfully.')
            return redirect('desk_list')

    context = {
        'active_page': 'desk_list',
        'desk': desk,
        'errors': errors,
    }
    return render(request, 'admin/desk_edit.html', context)


@admin_required
def desk_delete_view(request, pk):
    """
    Delete Desk staff and linked auth User.
    """
    desk = get_object_or_404(Desk, pk=pk)
    name = desk.name
    user = desk.user
    user.delete()

    messages.success(request, f'Desk user "{name}" has been deleted successfully.')
    return redirect('desk_list')


# ==========================================
# Social Media Management Views (Admin Control)
# ==========================================
@admin_required
def social_media_list_view(request):
    """
    Social Media Staff List with search, status filtering, and management actions (View, Edit, Delete).
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    social_media_members = SocialMedia.objects.all()

    if query:
        social_media_members = social_media_members.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    if status_filter == 'active':
        social_media_members = social_media_members.filter(is_active=True)
    elif status_filter == 'inactive':
        social_media_members = social_media_members.filter(is_active=False)

    context = {
        'active_page': 'social_media_list',
        'social_media_members': social_media_members,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'admin/social_media_list.html', context)


@admin_required
def social_media_add_view(request):
    """
    Add New Social Media Staff form.
    Fields: Name, Phone number, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
        }

        # Validation
        if not name:
            errors['name'] = "Social Media Staff Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif SocialMedia.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create SocialMedia Profile
            sm = SocialMedia.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                is_active=True
            )

            messages.success(request, f'Social Media user "{sm.name}" registered successfully!')
            return redirect('social_media_list')

    context = {
        'active_page': 'social_media_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/social_media_add.html', context)


@admin_required
def social_media_detail_view(request, pk):
    """
    View Social Media member full details / ID card.
    """
    sm = get_object_or_404(SocialMedia, pk=pk)
    context = {
        'active_page': 'social_media_list',
        'social_media': sm,
    }
    return render(request, 'admin/social_media_view.html', context)


@admin_required
def social_media_edit_view(request, pk):
    """
    Edit existing Social Media user information.
    """
    sm = get_object_or_404(SocialMedia, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif SocialMedia.objects.filter(phone_number=phone_number).exclude(pk=sm.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=sm.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            sm.name = name
            sm.is_active = is_active

            user = sm.user
            user.first_name = name
            user.is_active = is_active

            if phone_number != sm.phone_number:
                sm.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            sm.save()

            messages.success(request, f'Social Media user "{sm.name}" updated successfully.')
            return redirect('social_media_list')

    context = {
        'active_page': 'social_media_list',
        'social_media': sm,
        'errors': errors,
    }
    return render(request, 'admin/social_media_edit.html', context)


@admin_required
def social_media_delete_view(request, pk):
    """
    Delete Social Media staff and linked auth User.
    """
    sm = get_object_or_404(SocialMedia, pk=pk)
    name = sm.name
    user = sm.user
    user.delete()

    messages.success(request, f'Social Media user "{name}" has been deleted successfully.')
    return redirect('social_media_list')


# ==========================================
# Graphic Designer Management Views (Admin Control)
# ==========================================
@admin_required
def graphic_designer_list_view(request):
    """
    Graphic Designer Staff List with search, status filtering, and management actions (View, Edit, Delete).
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    designers = GraphicDesigner.objects.all()

    if query:
        designers = designers.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    if status_filter == 'active':
        designers = designers.filter(is_active=True)
    elif status_filter == 'inactive':
        designers = designers.filter(is_active=False)

    context = {
        'active_page': 'graphic_designer_list',
        'designers': designers,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'admin/graphic_designer_list.html', context)


@admin_required
def graphic_designer_add_view(request):
    """
    Add New Graphic Designer form.
    Fields: Name, Phone number, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
        }

        # Validation
        if not name:
            errors['name'] = "Graphic Designer Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif GraphicDesigner.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create GraphicDesigner Profile
            gd = GraphicDesigner.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                is_active=True
            )

            messages.success(request, f'Graphic Designer "{gd.name}" registered successfully!')
            return redirect('graphic_designer_list')

    context = {
        'active_page': 'graphic_designer_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/graphic_designer_add.html', context)


@admin_required
def graphic_designer_detail_view(request, pk):
    """
    View Graphic Designer full details / ID card.
    """
    designer = get_object_or_404(GraphicDesigner, pk=pk)
    context = {
        'active_page': 'graphic_designer_list',
        'designer': designer,
    }
    return render(request, 'admin/graphic_designer_view.html', context)


@admin_required
def graphic_designer_edit_view(request, pk):
    """
    Edit existing Graphic Designer information.
    """
    designer = get_object_or_404(GraphicDesigner, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif GraphicDesigner.objects.filter(phone_number=phone_number).exclude(pk=designer.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=designer.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            designer.name = name
            designer.is_active = is_active

            user = designer.user
            user.first_name = name
            user.is_active = is_active

            if phone_number != designer.phone_number:
                designer.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            designer.save()

            messages.success(request, f'Graphic Designer "{designer.name}" updated successfully.')
            return redirect('graphic_designer_list')

    context = {
        'active_page': 'graphic_designer_list',
        'designer': designer,
        'errors': errors,
    }
    return render(request, 'admin/graphic_designer_edit.html', context)


@admin_required
def graphic_designer_delete_view(request, pk):
    """
    Delete Graphic Designer staff and linked auth User.
    """
    designer = get_object_or_404(GraphicDesigner, pk=pk)
    name = designer.name
    user = designer.user
    user.delete()

    messages.success(request, f'Graphic Designer "{name}" has been deleted successfully.')
    return redirect('graphic_designer_list')




# ==========================================
# 4d. Input Management Views (Admin Control)
# ==========================================
@admin_required
def input_list_view(request):
    """
    List all Input staff with search, status filters, and action buttons.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    inputs_qs = InputUser.objects.all()

    if query:
        inputs_qs = inputs_qs.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    if status_filter == 'active':
        inputs_qs = inputs_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        inputs_qs = inputs_qs.filter(is_active=False)

    context = {
        'active_page': 'input_list',
        'inputs': inputs_qs,
        'query': query,
        'status_filter': status_filter,
        'total_count': InputUser.objects.count(),
    }
    return render(request, 'admin/input_list.html', context)


@admin_required
def input_add_view(request):
    """
    Add New Input staff form.
    Fields: Name, Phone number, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
        }

        # Validation
        if not name:
            errors['name'] = "Input Staff Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif InputUser.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create InputUser Profile
            inp = InputUser.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                is_active=True
            )

            messages.success(request, f'Input staff "{inp.name}" registered successfully!')
            return redirect('input_list')

    context = {
        'active_page': 'input_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/input_add.html', context)


@admin_required
def input_detail_view(request, pk):
    """
    View Input staff full details / ID card.
    """
    input_item = get_object_or_404(InputUser, pk=pk)
    context = {
        'active_page': 'input_list',
        'input_item': input_item,
    }
    return render(request, 'admin/input_view.html', context)


@admin_required
def input_edit_view(request, pk):
    """
    Edit existing Input staff information.
    """
    input_item = get_object_or_404(InputUser, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif InputUser.objects.filter(phone_number=phone_number).exclude(pk=input_item.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=input_item.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            input_item.name = name
            input_item.is_active = is_active

            user = input_item.user
            user.first_name = name
            user.is_active = is_active

            if phone_number != input_item.phone_number:
                input_item.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            input_item.save()

            messages.success(request, f'Input staff "{input_item.name}" updated successfully.')
            return redirect('input_list')

    context = {
        'active_page': 'input_list',
        'input_item': input_item,
        'errors': errors,
    }
    return render(request, 'admin/input_edit.html', context)


@admin_required
def input_delete_view(request, pk):
    """
    Delete Input staff and linked auth User.
    """
    input_item = get_object_or_404(InputUser, pk=pk)
    name = input_item.name
    user = input_item.user
    user.delete()

    messages.success(request, f'Input staff "{name}" has been deleted successfully.')
    return redirect('input_list')


# ==========================================
# Voice Over Management Views (Admin Control)
# ==========================================
@admin_required
def voice_over_list_view(request):
    """
    Voice Over staff list with search, status filtering, and management table.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    vo_qs = VoiceOverUser.objects.all()

    if query:
        vo_qs = vo_qs.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    if status_filter == 'active':
        vo_qs = vo_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        vo_qs = vo_qs.filter(is_active=False)

    context = {
        'active_page': 'voice_over_list',
        'voice_overs': vo_qs,
        'query': query,
        'status_filter': status_filter,
        'total_count': VoiceOverUser.objects.count(),
    }
    return render(request, 'admin/voice_over_list.html', context)


@admin_required
def voice_over_add_view(request):
    """
    Add New Voice Over staff form.
    Fields: Name, Phone number, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
        }

        # Validation
        if not name:
            errors['name'] = "Voice Over Staff Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif VoiceOverUser.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create VoiceOverUser Profile
            vo = VoiceOverUser.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                is_active=True
            )

            messages.success(request, f'Voice Over staff "{vo.name}" registered successfully!')
            return redirect('voice_over_list')

    context = {
        'active_page': 'voice_over_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/voice_over_add.html', context)


@admin_required
def voice_over_detail_view(request, pk):
    """
    View Voice Over staff full details / ID card.
    """
    vo_item = get_object_or_404(VoiceOverUser, pk=pk)
    context = {
        'active_page': 'voice_over_list',
        'vo_item': vo_item,
    }
    return render(request, 'admin/voice_over_view.html', context)


@admin_required
def voice_over_edit_view(request, pk):
    """
    Edit existing Voice Over staff information.
    """
    vo_item = get_object_or_404(VoiceOverUser, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif VoiceOverUser.objects.filter(phone_number=phone_number).exclude(pk=vo_item.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=vo_item.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            vo_item.name = name
            vo_item.is_active = is_active

            user = vo_item.user
            user.first_name = name
            user.is_active = is_active

            if phone_number != vo_item.phone_number:
                vo_item.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            vo_item.save()

            messages.success(request, f'Voice Over staff "{vo_item.name}" updated successfully.')
            return redirect('voice_over_list')

    context = {
        'active_page': 'voice_over_list',
        'vo_item': vo_item,
        'errors': errors,
    }
    return render(request, 'admin/voice_over_edit.html', context)


@admin_required
def voice_over_delete_view(request, pk):
    """
    Delete Voice Over staff and linked auth User.
    """
    vo_item = get_object_or_404(VoiceOverUser, pk=pk)
    name = vo_item.name
    user = vo_item.user
    user.delete()

    messages.success(request, f'Voice Over staff "{name}" has been deleted successfully.')
    return redirect('voice_over_list')


# ==========================================
# Copy Editor Management Views (Admin Control)
# ==========================================
@admin_required
def copy_editor_list_view(request):
    """
    Copy Editor staff list with search, status filtering, and management table.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    ce_qs = CopyEditor.objects.all()

    if query:
        ce_qs = ce_qs.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    if status_filter == 'active':
        ce_qs = ce_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        ce_qs = ce_qs.filter(is_active=False)

    context = {
        'active_page': 'copy_editor_list',
        'copy_editors': ce_qs,
        'query': query,
        'status_filter': status_filter,
        'total_count': CopyEditor.objects.count(),
    }
    return render(request, 'admin/copy_editor_list.html', context)


@admin_required
def copy_editor_add_view(request):
    """
    Add New Copy Editor form.
    Fields: Name, Phone number, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
        }

        # Validation
        if not name:
            errors['name'] = "Copy Editor Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif CopyEditor.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create CopyEditor Profile
            ce = CopyEditor.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                is_active=True
            )

            messages.success(request, f'Copy Editor "{ce.name}" registered successfully!')
            return redirect('copy_editor_list')

    context = {
        'active_page': 'copy_editor_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/copy_editor_add.html', context)


@admin_required
def copy_editor_detail_view(request, pk):
    """
    View Copy Editor full details / ID card.
    """
    ce_item = get_object_or_404(CopyEditor, pk=pk)
    context = {
        'active_page': 'copy_editor_list',
        'ce_item': ce_item,
    }
    return render(request, 'admin/copy_editor_view.html', context)


@admin_required
def copy_editor_edit_view(request, pk):
    """
    Edit existing Copy Editor information.
    """
    ce_item = get_object_or_404(CopyEditor, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif CopyEditor.objects.filter(phone_number=phone_number).exclude(pk=ce_item.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=ce_item.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            ce_item.name = name
            ce_item.is_active = is_active

            user = ce_item.user
            user.first_name = name
            user.is_active = is_active

            if phone_number != ce_item.phone_number:
                ce_item.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            ce_item.save()

            messages.success(request, f'Copy Editor "{ce_item.name}" updated successfully.')
            return redirect('copy_editor_list')

    context = {
        'active_page': 'copy_editor_list',
        'ce_item': ce_item,
        'errors': errors,
    }
    return render(request, 'admin/copy_editor_edit.html', context)


@admin_required
def copy_editor_delete_view(request, pk):
    """
    Delete Copy Editor and linked auth User.
    """
    ce_item = get_object_or_404(CopyEditor, pk=pk)
    name = ce_item.name
    user = ce_item.user
    user.delete()

    messages.success(request, f'Copy Editor "{name}" has been deleted successfully.')
    return redirect('copy_editor_list')


# ==========================================
# 4g. Visual Editor Management Views (Admin Control)
# ==========================================
@admin_required
def visual_editor_list_view(request):
    """
    Visual Editor staff list with search, status filtering, and management table.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    ve_qs = VisualEditor.objects.all()

    if query:
        ve_qs = ve_qs.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    if status_filter == 'active':
        ve_qs = ve_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        ve_qs = ve_qs.filter(is_active=False)

    context = {
        'active_page': 'visual_editor_list',
        'visual_editors': ve_qs,
        'query': query,
        'status_filter': status_filter,
        'total_count': VisualEditor.objects.count(),
    }
    return render(request, 'admin/visual_editor_list.html', context)


@admin_required
def visual_editor_add_view(request):
    """
    Add New Visual Editor form.
    Fields: Name, Phone number, Password, Confirm Password, and Save button.
    """
    errors = {}
    form_data = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        form_data = {
            'name': name,
            'phone_number': phone_number,
        }

        # Validation
        if not name:
            errors['name'] = "Visual Editor Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif VisualEditor.objects.filter(phone_number=phone_number).exists() or User.objects.filter(username=phone_number).exists():
            errors['phone_number'] = "An account with this Phone Number already exists."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 4:
            errors['password'] = "Password must be at least 4 characters long."

        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            # 1. Create Django Auth User
            user = User.objects.create_user(
                username=phone_number,
                first_name=name,
                password=password
            )

            # 2. Create VisualEditor Profile
            ve = VisualEditor.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                is_active=True
            )

            messages.success(request, f'Visual Editor "{ve.name}" registered successfully!')
            return redirect('visual_editor_list')

    context = {
        'active_page': 'visual_editor_add',
        'errors': errors,
        'form_data': form_data,
    }
    return render(request, 'admin/visual_editor_add.html', context)


@admin_required
def visual_editor_detail_view(request, pk):
    """
    View Visual Editor full details / ID card.
    """
    ve_item = get_object_or_404(VisualEditor, pk=pk)
    context = {
        'active_page': 'visual_editor_list',
        've_item': ve_item,
    }
    return render(request, 'admin/visual_editor_view.html', context)


@admin_required
def visual_editor_edit_view(request, pk):
    """
    Edit existing Visual Editor information.
    """
    ve_item = get_object_or_404(VisualEditor, pk=pk)
    errors = {}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == '1'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name:
            errors['name'] = "Name is required."

        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif VisualEditor.objects.filter(phone_number=phone_number).exclude(pk=ve_item.pk).exists() or \
             User.objects.filter(username=phone_number).exclude(pk=ve_item.user.pk).exists():
            errors['phone_number'] = "Another account with this Phone Number already exists."

        if new_password:
            if len(new_password) < 4:
                errors['new_password'] = "Password must be at least 4 characters long."
            if new_password != confirm_password:
                errors['confirm_password'] = "Passwords do not match."

        if not errors:
            ve_item.name = name
            ve_item.is_active = is_active

            user = ve_item.user
            user.first_name = name
            user.is_active = is_active

            if phone_number != ve_item.phone_number:
                ve_item.phone_number = phone_number
                user.username = phone_number

            if new_password:
                user.set_password(new_password)

            user.save()
            ve_item.save()

            messages.success(request, f'Visual Editor "{ve_item.name}" updated successfully.')
            return redirect('visual_editor_list')

    context = {
        'active_page': 'visual_editor_list',
        've_item': ve_item,
        'errors': errors,
    }
    return render(request, 'admin/visual_editor_edit.html', context)


@admin_required
def visual_editor_delete_view(request, pk):
    """
    Delete Visual Editor and linked auth User.
    """
    ve_item = get_object_or_404(VisualEditor, pk=pk)
    name = ve_item.name
    user = ve_item.user
    user.delete()

    messages.success(request, f'Visual Editor "{name}" has been deleted successfully.')
    return redirect('visual_editor_list')




# ==========================================
# Reporter Portal Views (Separate Section)
# ==========================================
# ==========================================
# Schema management functions previously here have been disabled.
# Django migrations are the single source of truth for the database schema.
# ==========================================
def _ensure_teleprompter_table():
    pass

def _ensure_chat_table():
    pass

def _ensure_copy_chat_table():
    pass

def _ensure_voice_over_chat_table():
    pass

def _ensure_social_media_chat_table():
    pass

def _ensure_reporter_chat_table():
    pass


# ==========================================
@reporter_required
def reporter_dashboard_view(request):
    """
    Reporter's Personal Dashboard.
    """
    _ensure_teleprompter_table()
    reporter = request.user.reporter_profile
    user_news_qs = News.objects.filter(Q(reporter=reporter) | Q(author=request.user))
    my_news_count = user_news_qs.count()
    approved_count = user_news_qs.filter(status='Approved').count()
    rejected_count = user_news_qs.filter(status='Rejected').count()
    pending_count = user_news_qs.filter(status='Submitted').count()
    recent_news = user_news_qs.order_by('-created_at')[:6]

    # Teleprompter scripts assigned to this reporter by Desk
    prompter_qs = TeleprompterScript.objects.filter(reporter=reporter).order_by('-created_at')
    unread_prompter_count = prompter_qs.filter(is_read=False).count()
    latest_prompter = prompter_qs.first()

    context = {
        'active_page': 'reporter_dashboard',
        'reporter': reporter,
        'my_news_count': my_news_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pending_count': pending_count,
        'recent_news': recent_news,
        'unread_prompter_count': unread_prompter_count,
        'latest_prompter': latest_prompter,
        'total_prompters_count': prompter_qs.count(),
    }
    return render(request, 'reporter/dashboard.html', context)


@reporter_required
def reporter_profile_view(request):
    """
    Reporter's Personal Profile & ID Card View.
    """
    _ensure_teleprompter_table()
    reporter = request.user.reporter_profile
    prompter_qs = TeleprompterScript.objects.filter(reporter=reporter)
    unread_prompter_count = prompter_qs.filter(is_read=False).count()

    context = {
        'active_page': 'reporter_profile',
        'reporter': reporter,
        'unread_prompter_count': unread_prompter_count,
    }
    return render(request, 'reporter/profile.html', context)


@reporter_required
def reporter_teleprompter_view(request, pk=None):
    """
    Reporter's Personal Broadcast Teleprompter Studio:
    Displays ONLY scripts dispatched by Desk to this specific reporter.
    Provides auto-scroll, speed controls, play/pause, font sizing,
    broadcast dark mode, mirror flip mode, and full-screen reading.
    """
    _ensure_teleprompter_table()
    reporter = request.user.reporter_profile

    # Strictly filter ONLY scripts sent to THIS reporter!
    scripts = TeleprompterScript.objects.select_related('desk', 'news').filter(reporter=reporter).order_by('-created_at')

    active_script = None
    if pk:
        active_script = get_object_or_404(TeleprompterScript, pk=pk, reporter=reporter)
    elif scripts.exists():
        active_script = scripts.first()

    if active_script and not active_script.is_read:
        active_script.is_read = True
        active_script.read_at = timezone.now()
        active_script.save(update_fields=['is_read', 'read_at'])

    unread_count = scripts.filter(is_read=False).count()

    context = {
        'active_page': 'reporter_teleprompter',
        'reporter': reporter,
        'scripts': scripts,
        'active_script': active_script,
        'unread_prompter_count': unread_count,
        'total_scripts_count': scripts.count(),
    }
    return render(request, 'reporter/teleprompter.html', context)


# ==========================================
# Reporter <-> Desk Chat Views
# ==========================================
@reporter_required
def reporter_chat_desk_view(request, desk_id=None):
    """
    Chat portal for Reporter to communicate directly with Desk staff.
    Lists all Desk staff, shows unread messages from Desk, and opens conversation thread.
    """
    _ensure_reporter_chat_table()
    reporter = getattr(request.user, 'reporter_profile', None)
    if not reporter:
        messages.error(request, "No Reporter profile found.")
        return redirect('reporter_dashboard')

    desks = list(Desk.objects.filter(is_active=True).order_by('name'))

    for d in desks:
        d_status = d.get_last_seen_info()
        d.is_online = d_status['is_online']
        d.last_seen_text = d_status['text']
        d.unread_count = DeskReporterChatMessage.objects.filter(
            desk=d,
            reporter=reporter,
            sender_type='desk',
            is_read=False
        ).count()
        latest_msg = DeskReporterChatMessage.objects.filter(
            desk=d,
            reporter=reporter
        ).order_by('-created_at').first()
        d.latest_message = latest_msg

    active_desk = None
    if desk_id:
        active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    elif desks:
        desks_with_msg = [d for d in desks if d.latest_message]
        if desks_with_msg:
            desks_with_msg.sort(key=lambda d: (d.unread_count > 0, d.latest_message.created_at), reverse=True)
            active_desk = desks_with_msg[0]
        else:
            active_desk = desks[0]

    chat_messages = []
    if active_desk:
        desk_status = active_desk.get_last_seen_info()
        active_desk.is_online = desk_status['is_online']
        active_desk.last_seen_text = desk_status['text']

        # Mark unread messages from this Desk as read
        DeskReporterChatMessage.objects.filter(
            desk=active_desk,
            reporter=reporter,
            sender_type='desk',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskReporterChatMessage.objects.filter(
            desk=active_desk,
            reporter=reporter
        ).order_by('created_at')

    context = {
        'active_page': 'reporter_chat_desk',
        'reporter': reporter,
        'desks': desks,
        'active_desk': active_desk,
        'chat_messages': chat_messages,
    }
    return render(request, 'reporter/chat_desk.html', context)


@reporter_required
def reporter_send_chat_message_view(request, desk_id):
    """
    POST/AJAX endpoint for Reporter to send a message to Desk.
    """
    _ensure_reporter_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    reporter = getattr(request.user, 'reporter_profile', None)
    if not reporter:
        return JsonResponse({'success': False, 'error': 'Reporter profile not found.'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskReporterChatMessage.objects.create(
        desk=active_desk,
        reporter=reporter,
        sender_type='reporter',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    Reporter.objects.filter(pk=reporter.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': reporter.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('reporter_chat_desk_with_desk', desk_id=active_desk.pk)


@reporter_required
def reporter_get_chat_messages_api(request, desk_id):
    """
    GET AJAX polling endpoint for Reporter chatting with Desk.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Desk as read.
    """
    _ensure_reporter_chat_table()
    reporter = getattr(request.user, 'reporter_profile', None)
    if not reporter:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskReporterChatMessage.objects.filter(
        desk=active_desk,
        reporter=reporter,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='desk', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskReporterChatMessage.objects.filter(
        reporter=reporter,
        sender_type='desk',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': active_desk.name if m.sender_type == 'desk' else reporter.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': timezone.localtime(m.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(m.created_at).strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    Reporter.objects.filter(pk=reporter.pk).update(last_seen=timezone.now())

    active_desk.refresh_from_db()
    desk_status = active_desk.get_last_seen_info()

    read_message_ids = list(DeskReporterChatMessage.objects.filter(
        desk=active_desk,
        reporter=reporter,
        sender_type='reporter',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': desk_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Desk Portal Views (Separate Section)
# ==========================================
@desk_required
def desk_dashboard_view(request):
    """
    Desk Staff Personal Dashboard.
    Shows approved stories from Input Desk ready for broadcast telecast & production.
    """
    desk = getattr(request.user, 'desk_profile', None)
    total_reporters = Reporter.objects.count()
    active_reporters = Reporter.objects.filter(is_active=True).count()
    districts_count = Reporter.objects.values('district').distinct().count()
    recent_reporters = Reporter.objects.all()[:6]

    # Desk 'My Word' news: Stories verified and selected by the Input Desk (status='Approved')
    sent_condition = (
        Q(assigned_at__isnull=False) |
        Q(assigned_voice_over__isnull=False) |
        Q(assigned_copy_editor__isnull=False) |
        Q(assigned_graphic_designer__isnull=False) |
        Q(assigned_visual_editor__isnull=False) |
        Q(assigned_social_media__isnull=False) |
        Q(sent_to_social_media=True)
    )
    my_word_qs = News.objects.select_related('reporter', 'author').prefetch_related('additional_media').filter(status='Approved')
    total_approved = my_word_qs.count()
    sent_work_count = my_word_qs.filter(sent_condition).distinct().count()
    pending_word_count = my_word_qs.filter(~sent_condition).distinct().count()

    my_word_today_count = my_word_qs.filter(created_at__date=timezone.now().date()).count()
    my_word_news = my_word_qs.order_by('-created_at')[:8]

    context = {
        'active_page': 'desk_dashboard',
        'desk': desk,
        'total_reporters': total_reporters,
        'active_reporters': active_reporters,
        'districts_count': districts_count,
        'recent_reporters': recent_reporters,
        'total_news': total_approved,
        'recent_news': my_word_news,
        'my_word_count': pending_word_count,
        'sent_work_count': sent_work_count,
        'my_word_today_count': my_word_today_count,
        'my_word_news': my_word_news,
    }
    return render(request, 'desk/dashboard.html', context)


@desk_required
def desk_my_word_view(request):
    """
    Desk Staff 'My Work' Portal:
    Displays news stories verified and selected by the Input Desk.
    Defaults to Pending stories waiting to be dispatched, with tab to view all.
    """
    _ensure_copy_editor_columns()
    desk = getattr(request.user, 'desk_profile', None)
    today = timezone.now().date()
    today_str = today.strftime('%Y-%m-%d')
    selected_date = request.GET.get('date', 'all').strip()
    query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()
    district_filter = request.GET.get('district', '').strip()
    dispatch_tab = request.GET.get('dispatch', 'pending').strip()

    sent_condition = (
        Q(assigned_at__isnull=False) |
        Q(assigned_voice_over__isnull=False) |
        Q(assigned_copy_editor__isnull=False) |
        Q(assigned_graphic_designer__isnull=False) |
        Q(assigned_visual_editor__isnull=False) |
        Q(assigned_social_media__isnull=False) |
        Q(sent_to_social_media=True)
    )

    # Base Query: news selected/approved by Input Desk
    base_qs = News.objects.select_related(
        'reporter', 'author',
        'assigned_copy_editor', 'edited_by_copy_editor', 'assigned_visual_editor',
        'assigned_voice_over', 'assigned_graphic_designer',
        'assigned_social_media'
    ).prefetch_related('additional_media').filter(status='Approved')
    
    total_approved_all = base_qs.count()
    sent_work_count = base_qs.filter(sent_condition).distinct().count()
    pending_word_count = base_qs.filter(~sent_condition).distinct().count()
    today_approved_count = base_qs.filter(created_at__date=today).count()

    if dispatch_tab == 'pending':
        news_qs = base_qs.filter(~sent_condition).distinct()
    elif dispatch_tab == 'sent':
        news_qs = base_qs.filter(sent_condition).distinct()
    else:
        news_qs = base_qs

    # Date filter
    if selected_date and selected_date != 'all':
        if selected_date == 'today':
            selected_date = today_str
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            news_qs = news_qs.filter(created_at__date=filter_date)
        except ValueError:
            selected_date = 'all'

    if query:
        news_qs = news_qs.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(district__icontains=query) |
            Q(reporter__name__icontains=query) |
            Q(reporter__reporter_id__icontains=query)
        )

    if type_filter:
        news_qs = news_qs.filter(news_type=type_filter)

    if district_filter:
        news_qs = news_qs.filter(district__iexact=district_filter)

    current_list_count = news_qs.count()
    all_districts = base_qs.values_list('district', flat=True).distinct().order_by('district')

    from .middleware import touch_user_last_seen
    touch_user_last_seen(request.user, timezone.now())

    copy_editors = sorted(CopyEditor.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    visual_editors = sorted(VisualEditor.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    voice_overs = sorted(VoiceOverUser.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    graphic_designers = sorted(GraphicDesigner.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    social_medias = sorted(SocialMedia.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))

    context = {
        'active_page': 'desk_my_word',
        'desk': desk,
        'news_list': news_qs,
        'total_approved_all': total_approved_all,
        'today_approved_count': today_approved_count,
        'current_list_count': current_list_count,
        'my_word_count': pending_word_count,
        'pending_word_count': pending_word_count,
        'sent_work_count': sent_work_count,
        'dispatch_tab': dispatch_tab,
        'selected_date': selected_date,
        'today_str': today_str,
        'query': query,
        'type_filter': type_filter,
        'district_filter': district_filter,
        'all_districts': all_districts,
        'news_types': [c[0] for c in NEWS_TYPE_CHOICES],
        'copy_editors': copy_editors,
        'visual_editors': visual_editors,
        'voice_overs': voice_overs,
        'graphic_designers': graphic_designers,
        'social_medias': social_medias,
    }
    return render(request, 'desk/my_word.html', context)


@desk_required
def desk_my_work_list_view(request):
    """
    Desk Staff 'My Work List' Portal:
    Displays all news stories dispatched/sent to team members:
    Voice Over, Copy Editor, Graphic Designer, Visual Editor, and Social Media.
    Shows exactly who each story was sent to, desk notes, and dispatched timestamp.
    """
    _ensure_copy_editor_columns()
    desk = getattr(request.user, 'desk_profile', None)
    today = timezone.now().date()
    today_str = today.strftime('%Y-%m-%d')
    selected_date = request.GET.get('date', 'all').strip()
    query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()
    district_filter = request.GET.get('district', '').strip()
    role_filter = request.GET.get('role', 'all').strip()

    sent_condition = (
        Q(assigned_at__isnull=False) |
        Q(assigned_voice_over__isnull=False) |
        Q(assigned_copy_editor__isnull=False) |
        Q(assigned_graphic_designer__isnull=False) |
        Q(assigned_visual_editor__isnull=False) |
        Q(assigned_social_media__isnull=False) |
        Q(sent_to_social_media=True)
    )

    base_sent_qs = News.objects.select_related(
        'reporter', 'author',
        'assigned_copy_editor', 'edited_by_copy_editor', 'assigned_visual_editor',
        'assigned_voice_over', 'assigned_graphic_designer',
        'assigned_social_media'
    ).prefetch_related('additional_media').filter(status='Approved').filter(sent_condition).distinct().order_by('-assigned_at', '-created_at')

    news_qs = base_sent_qs

    # Date filter
    if selected_date and selected_date != 'all':
        if selected_date == 'today':
            selected_date = today_str
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            news_qs = news_qs.filter(assigned_at__date=filter_date)
        except ValueError:
            selected_date = 'all'

    # Keyword Search
    if query:
        news_qs = news_qs.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(district__icontains=query) |
            Q(reporter__name__icontains=query) |
            Q(desk_notes__icontains=query) |
            Q(assigned_voice_over__name__icontains=query) |
            Q(assigned_copy_editor__name__icontains=query) |
            Q(assigned_graphic_designer__name__icontains=query) |
            Q(assigned_visual_editor__name__icontains=query) |
            Q(assigned_social_media__name__icontains=query)
        )

    # Format filter
    if type_filter:
        news_qs = news_qs.filter(news_type=type_filter)

    # District filter
    if district_filter:
        news_qs = news_qs.filter(district__iexact=district_filter)

    # Role filter
    if role_filter == 'voice_over':
        news_qs = news_qs.filter(assigned_voice_over__isnull=False)
    elif role_filter == 'copy_editor':
        news_qs = news_qs.filter(assigned_copy_editor__isnull=False)
    elif role_filter == 'graphic_designer':
        news_qs = news_qs.filter(assigned_graphic_designer__isnull=False)
    elif role_filter == 'visual_editor':
        news_qs = news_qs.filter(assigned_visual_editor__isnull=False)
    elif role_filter == 'social_media':
        news_qs = news_qs.filter(Q(assigned_social_media__isnull=False) | Q(sent_to_social_media=True))

    total_sent_count = base_sent_qs.count()
    vo_sent_count = base_sent_qs.filter(assigned_voice_over__isnull=False).count()
    ce_sent_count = base_sent_qs.filter(assigned_copy_editor__isnull=False).count()
    gd_sent_count = base_sent_qs.filter(assigned_graphic_designer__isnull=False).count()
    ve_sent_count = base_sent_qs.filter(assigned_visual_editor__isnull=False).count()
    sm_sent_count = base_sent_qs.filter(Q(assigned_social_media__isnull=False) | Q(sent_to_social_media=True)).count()

    base_all_qs = News.objects.filter(status='Approved')
    pending_word_count = base_all_qs.filter(~sent_condition).distinct().count()

    all_districts = base_sent_qs.values_list('district', flat=True).distinct().order_by('district')

    from .middleware import touch_user_last_seen
    touch_user_last_seen(request.user, timezone.now())

    copy_editors = sorted(CopyEditor.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    visual_editors = sorted(VisualEditor.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    voice_overs = sorted(VoiceOverUser.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    graphic_designers = sorted(GraphicDesigner.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))
    social_medias = sorted(SocialMedia.objects.filter(is_active=True), key=lambda x: (not x.is_online, x.name))

    context = {
        'active_page': 'desk_my_work_list',
        'desk': desk,
        'news_list': news_qs,
        'current_list_count': news_qs.count(),
        'total_sent_count': total_sent_count,
        'sent_work_count': total_sent_count,
        'my_word_count': pending_word_count,
        'vo_sent_count': vo_sent_count,
        'ce_sent_count': ce_sent_count,
        'gd_sent_count': gd_sent_count,
        've_sent_count': ve_sent_count,
        'sm_sent_count': sm_sent_count,
        'selected_date': selected_date,
        'today_str': today_str,
        'query': query,
        'type_filter': type_filter,
        'district_filter': district_filter,
        'role_filter': role_filter,
        'all_districts': all_districts,
        'news_types': [c[0] for c in NEWS_TYPE_CHOICES],
        'copy_editors': copy_editors,
        'visual_editors': visual_editors,
        'voice_overs': voice_overs,
        'graphic_designers': graphic_designers,
        'social_medias': social_medias,
    }
    return render(request, 'desk/my_work_list.html', context)


@desk_required
def desk_profile_view(request):
    """
    Desk Staff Personal Profile & Workspace Info.
    """
    desk = getattr(request.user, 'desk_profile', None)
    sent_condition = (
        Q(assigned_at__isnull=False) |
        Q(assigned_voice_over__isnull=False) |
        Q(assigned_copy_editor__isnull=False) |
        Q(assigned_graphic_designer__isnull=False) |
        Q(assigned_visual_editor__isnull=False) |
        Q(assigned_social_media__isnull=False) |
        Q(sent_to_social_media=True)
    )
    base_qs = News.objects.filter(status='Approved')
    pending_word_count = base_qs.filter(~sent_condition).distinct().count()
    sent_work_count = base_qs.filter(sent_condition).distinct().count()

    context = {
        'active_page': 'desk_profile',
        'desk': desk,
        'my_word_count': pending_word_count,
        'sent_work_count': sent_work_count,
    }
    return render(request, 'desk/profile.html', context)


@desk_required
def desk_teleprompter_view(request):
    """
    Desk Staff Teleprompter Dispatcher:
    Allows Desk to draft or select broadcast scripts, choose a specific reporter,
    and dispatch it directly to their teleprompter in real-time.
    """
    _ensure_teleprompter_table()
    desk = getattr(request.user, 'desk_profile', None)

    if request.method == 'POST':
        # Support both multiple reporter_ids and single reporter_id
        reporter_ids = request.POST.getlist('reporter_ids')
        if not reporter_ids:
            single_id = request.POST.get('reporter_id')
            if single_id:
                reporter_ids = [single_id]

        title = request.POST.get('title', '').strip()
        script_text = request.POST.get('script_text', '').strip()
        news_id = request.POST.get('news_id')

        if not reporter_ids:
            messages.error(request, "Please choose at least one Reporter to send the teleprompter script.")
            return redirect('desk_teleprompter')

        if not script_text:
            messages.error(request, "Please enter teleprompter script text before sending.")
            return redirect('desk_teleprompter')

        selected_reporters = list(Reporter.objects.filter(pk__in=reporter_ids, is_active=True))
        if not selected_reporters:
            messages.error(request, "Selected reporter(s) not found or inactive.")
            return redirect('desk_teleprompter')

        news = None
        if news_id:
            try:
                news = News.objects.get(pk=news_id)
            except (News.DoesNotExist, ValueError):
                news = None

        if not title:
            if news:
                title = news.headline[:80]
            else:
                title = f"Teleprompter Cue - {timezone.now().strftime('%d %b, %H:%M')}"

        now = timezone.now()
        created_names = []
        for rep in selected_reporters:
            TeleprompterScript.objects.create(
                reporter=rep,
                desk=desk,
                news=news,
                title=title,
                script_text=script_text,
                is_read=False,
                created_at=now,
                updated_at=now,
            )
            created_names.append(rep.name)

        if len(created_names) == 1:
            messages.success(request, f"✓ Teleprompter script sent successfully to Reporter {created_names[0]}!")
        else:
            names_summary = ", ".join(created_names[:3])
            if len(created_names) > 3:
                names_summary += f" and {len(created_names) - 3} others"
            messages.success(request, f"✓ Teleprompter script sent successfully to {len(created_names)} Reporters ({names_summary})!")
        return redirect('desk_teleprompter')

    reporters = Reporter.objects.filter(is_active=True).order_by('district', 'name')
    sent_scripts = TeleprompterScript.objects.select_related('reporter', 'news', 'desk').order_by('-created_at')[:50]
    approved_news = News.objects.filter(status='Approved').order_by('-created_at')[:30]

    selected_reporter_id = request.GET.get('reporter', '')
    selected_news_id = request.GET.get('news', '')

    context = {
        'active_page': 'desk_teleprompter',
        'desk': desk,
        'reporters': reporters,
        'sent_scripts': sent_scripts,
        'approved_news': approved_news,
        'selected_reporter_id': selected_reporter_id,
        'selected_news_id': selected_news_id,
    }
    return render(request, 'desk/teleprompter.html', context)


@desk_required
def desk_teleprompter_delete_view(request, pk):
    """Delete a sent teleprompter script from Desk history"""
    _ensure_teleprompter_table()
    script = get_object_or_404(TeleprompterScript, pk=pk)
    rep_name = script.reporter.name if script.reporter else "Reporter"
    script.delete()
    messages.info(request, f"Teleprompter script for {rep_name} removed.")
    return redirect('desk_teleprompter')


# ==========================================
# Desk <-> Visual Editor Chat Views
# ==========================================
@desk_required
def desk_chat_visual_editor_view(request, ve_id=None):
    """
    Chat portal for Desk staff to communicate directly with Visual Editors.
    Lists all visual editors, shows unread message counts, latest message preview,
    and opens the conversation thread.
    """
    _ensure_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        messages.error(request, "No Desk profile found for this user account.")
        return redirect('desk_dashboard')

    visual_editors = list(VisualEditor.objects.filter(is_active=True).order_by('name'))

    for ve in visual_editors:
        ve_status = ve.get_last_seen_info()
        ve.is_online = ve_status['is_online']
        ve.last_seen_text = ve_status['text']
        ve.unread_count = DeskVisualChatMessage.objects.filter(
            desk=desk,
            visual_editor=ve,
            sender_type='visual_editor',
            is_read=False
        ).count()
        latest_msg = DeskVisualChatMessage.objects.filter(
            desk=desk,
            visual_editor=ve
        ).order_by('-created_at').first()
        ve.latest_message = latest_msg

    active_ve = None
    if ve_id:
        active_ve = get_object_or_404(VisualEditor, pk=ve_id, is_active=True)
    elif visual_editors:
        # Default to the visual editor with the most recent message or the first one
        ves_with_msg = [v for v in visual_editors if v.latest_message]
        if ves_with_msg:
            ves_with_msg.sort(key=lambda v: (v.unread_count > 0, v.latest_message.created_at), reverse=True)
            active_ve = ves_with_msg[0]
        else:
            active_ve = visual_editors[0]

    chat_messages = []
    if active_ve:
        ve_status = active_ve.get_last_seen_info()
        active_ve.is_online = ve_status['is_online']
        active_ve.last_seen_text = ve_status['text']

        # Mark all unread messages from this VE as read
        DeskVisualChatMessage.objects.filter(
            desk=desk,
            visual_editor=active_ve,
            sender_type='visual_editor',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskVisualChatMessage.objects.filter(
            desk=desk,
            visual_editor=active_ve
        ).order_by('created_at')

    context = {
        'active_page': 'desk_chat_visual_editor',
        'desk_user': desk,
        'visual_editors': visual_editors,
        'active_ve': active_ve,
        'chat_messages': chat_messages,
    }
    return render(request, 'desk/chat_visual_editor.html', context)


@desk_required
def desk_send_chat_message_view(request, ve_id):
    """
    POST/AJAX endpoint for Desk to send a message to a Visual Editor.
    """
    _ensure_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Desk profile not found.'}, status=403)

    active_ve = get_object_or_404(VisualEditor, pk=ve_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskVisualChatMessage.objects.create(
        desk=desk,
        visual_editor=active_ve,
        sender_type='desk',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': desk.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('desk_chat_visual_editor_with_ve', ve_id=active_ve.pk)


@desk_required
def desk_get_chat_messages_api(request, ve_id):
    """
    GET AJAX polling endpoint for Desk.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Visual Editor as read.
    """
    _ensure_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_ve = get_object_or_404(VisualEditor, pk=ve_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskVisualChatMessage.objects.filter(
        desk=desk,
        visual_editor=active_ve,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='visual_editor', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskVisualChatMessage.objects.filter(
        desk=desk,
        sender_type='visual_editor',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': desk.name if m.sender_type == 'desk' else active_ve.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': m.created_at.strftime('%I:%M %p'),
            'date_formatted': m.created_at.strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    active_ve.refresh_from_db(fields=['last_seen'])
    ve_status = active_ve.get_last_seen_info()

    read_message_ids = list(DeskVisualChatMessage.objects.filter(
        desk=desk,
        visual_editor=active_ve,
        sender_type='desk',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': ve_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Desk <-> Copy Editor Chat Views
# ==========================================
@desk_required
def desk_chat_copy_editor_view(request, ce_id=None):
    """
    Chat portal for Desk staff to communicate directly with Copy Editors.
    Lists all copy editors, shows unread message counts, latest message preview,
    and opens the conversation thread.
    """
    _ensure_copy_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        messages.error(request, "No Desk profile found for this user account.")
        return redirect('desk_dashboard')

    copy_editors = list(CopyEditor.objects.filter(is_active=True).order_by('name'))

    for ce in copy_editors:
        ce_status = ce.get_last_seen_info()
        ce.is_online = ce_status['is_online']
        ce.last_seen_text = ce_status['text']
        ce.unread_count = DeskCopyChatMessage.objects.filter(
            desk=desk,
            copy_editor=ce,
            sender_type='copy_editor',
            is_read=False
        ).count()
        latest_msg = DeskCopyChatMessage.objects.filter(
            desk=desk,
            copy_editor=ce
        ).order_by('-created_at').first()
        ce.latest_message = latest_msg

    active_ce = None
    if ce_id:
        active_ce = get_object_or_404(CopyEditor, pk=ce_id, is_active=True)
    elif copy_editors:
        # Default to the copy editor with the most recent message or the first one
        ces_with_msg = [c for c in copy_editors if c.latest_message]
        if ces_with_msg:
            ces_with_msg.sort(key=lambda c: (c.unread_count > 0, c.latest_message.created_at), reverse=True)
            active_ce = ces_with_msg[0]
        else:
            active_ce = copy_editors[0]

    chat_messages = []
    if active_ce:
        ce_status = active_ce.get_last_seen_info()
        active_ce.is_online = ce_status['is_online']
        active_ce.last_seen_text = ce_status['text']

        # Mark all unread messages from this CE as read
        DeskCopyChatMessage.objects.filter(
            desk=desk,
            copy_editor=active_ce,
            sender_type='copy_editor',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskCopyChatMessage.objects.filter(
            desk=desk,
            copy_editor=active_ce
        ).order_by('created_at')

    context = {
        'active_page': 'desk_chat_copy_editor',
        'desk_user': desk,
        'copy_editors': copy_editors,
        'active_ce': active_ce,
        'chat_messages': chat_messages,
    }
    return render(request, 'desk/chat_copy_editor.html', context)


@desk_required
def desk_send_copy_chat_message_view(request, ce_id):
    """
    POST/AJAX endpoint for Desk to send a message to a Copy Editor.
    """
    _ensure_copy_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Desk profile not found.'}, status=403)

    active_ce = get_object_or_404(CopyEditor, pk=ce_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskCopyChatMessage.objects.create(
        desk=desk,
        copy_editor=active_ce,
        sender_type='desk',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': desk.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('desk_chat_copy_editor_with_ce', ce_id=active_ce.pk)


@desk_required
def desk_get_copy_chat_messages_api(request, ce_id):
    """
    GET AJAX polling endpoint for Desk chatting with Copy Editor.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Copy Editor as read.
    """
    _ensure_copy_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_ce = get_object_or_404(CopyEditor, pk=ce_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskCopyChatMessage.objects.filter(
        desk=desk,
        copy_editor=active_ce,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='copy_editor', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskCopyChatMessage.objects.filter(
        desk=desk,
        sender_type='copy_editor',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': desk.name if m.sender_type == 'desk' else active_ce.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': m.created_at.strftime('%I:%M %p'),
            'date_formatted': m.created_at.strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    active_ce.refresh_from_db(fields=['last_seen'])
    ce_status = active_ce.get_last_seen_info()

    read_message_ids = list(DeskCopyChatMessage.objects.filter(
        desk=desk,
        copy_editor=active_ce,
        sender_type='desk',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': ce_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Desk <-> Voice Over Chat Views
# ==========================================
@desk_required
def desk_chat_voice_over_view(request, vo_id=None):
    """
    Chat portal for Desk staff to communicate directly with Voice Over staff.
    Lists all voice over staff, shows unread message counts, latest message preview,
    and opens the conversation thread.
    """
    _ensure_voice_over_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        messages.error(request, "No Desk profile found for this user account.")
        return redirect('desk_dashboard')

    voice_overs = list(VoiceOverUser.objects.filter(is_active=True).order_by('name'))

    for vo in voice_overs:
        vo_status = vo.get_last_seen_info()
        vo.is_online = vo_status['is_online']
        vo.last_seen_text = vo_status['text']
        vo.unread_count = DeskVoiceOverChatMessage.objects.filter(
            desk=desk,
            voice_over=vo,
            sender_type='voice_over',
            is_read=False
        ).count()
        latest_msg = DeskVoiceOverChatMessage.objects.filter(
            desk=desk,
            voice_over=vo
        ).order_by('-created_at').first()
        vo.latest_message = latest_msg

    active_vo = None
    if vo_id:
        active_vo = get_object_or_404(VoiceOverUser, pk=vo_id, is_active=True)
    elif voice_overs:
        # Default to the voice over staff with the most recent message or the first one
        vos_with_msg = [v for v in voice_overs if v.latest_message]
        if vos_with_msg:
            vos_with_msg.sort(key=lambda v: (v.unread_count > 0, v.latest_message.created_at), reverse=True)
            active_vo = vos_with_msg[0]
        else:
            active_vo = voice_overs[0]

    chat_messages = []
    if active_vo:
        vo_status = active_vo.get_last_seen_info()
        active_vo.is_online = vo_status['is_online']
        active_vo.last_seen_text = vo_status['text']

        # Mark all unread messages from this VO as read
        DeskVoiceOverChatMessage.objects.filter(
            desk=desk,
            voice_over=active_vo,
            sender_type='voice_over',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskVoiceOverChatMessage.objects.filter(
            desk=desk,
            voice_over=active_vo
        ).order_by('created_at')

    context = {
        'active_page': 'desk_chat_voice_over',
        'desk_user': desk,
        'voice_overs': voice_overs,
        'active_vo': active_vo,
        'chat_messages': chat_messages,
    }
    return render(request, 'desk/chat_voice_over.html', context)


@desk_required
def desk_send_voice_over_chat_message_view(request, vo_id):
    """
    POST/AJAX endpoint for Desk to send a message to Voice Over staff.
    """
    _ensure_voice_over_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Desk profile not found.'}, status=403)

    active_vo = get_object_or_404(VoiceOverUser, pk=vo_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskVoiceOverChatMessage.objects.create(
        desk=desk,
        voice_over=active_vo,
        sender_type='desk',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': desk.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('desk_chat_voice_over_with_vo', vo_id=active_vo.pk)


@desk_required
def desk_get_voice_over_chat_messages_api(request, vo_id):
    """
    GET AJAX polling endpoint for Desk chatting with Voice Over staff.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Voice Over as read.
    """
    _ensure_voice_over_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_vo = get_object_or_404(VoiceOverUser, pk=vo_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskVoiceOverChatMessage.objects.filter(
        desk=desk,
        voice_over=active_vo,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='voice_over', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskVoiceOverChatMessage.objects.filter(
        desk=desk,
        sender_type='voice_over',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': desk.name if m.sender_type == 'desk' else active_vo.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': m.created_at.strftime('%I:%M %p'),
            'date_formatted': m.created_at.strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    active_vo.refresh_from_db(fields=['last_seen'])
    vo_status = active_vo.get_last_seen_info()

    read_message_ids = list(DeskVoiceOverChatMessage.objects.filter(
        desk=desk,
        voice_over=active_vo,
        sender_type='desk',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': vo_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Desk <-> Social Media Chat Views
# ==========================================
@desk_required
def desk_chat_social_media_view(request, sm_id=None):
    """
    Chat portal for Desk staff to communicate directly with Social Media staff.
    Lists all Social Media staff, shows unread message counts, latest message preview,
    and opens the conversation thread.
    """
    _ensure_social_media_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        messages.error(request, "No Desk profile found for this user account.")
        return redirect('desk_dashboard')

    social_medias = list(SocialMedia.objects.filter(is_active=True).order_by('name'))

    for sm in social_medias:
        sm_status = sm.get_last_seen_info()
        sm.is_online = sm_status['is_online']
        sm.last_seen_text = sm_status['text']
        sm.unread_count = DeskSocialChatMessage.objects.filter(
            desk=desk,
            social_media=sm,
            sender_type='social_media',
            is_read=False
        ).count()
        latest_msg = DeskSocialChatMessage.objects.filter(
            desk=desk,
            social_media=sm
        ).order_by('-created_at').first()
        sm.latest_message = latest_msg

    active_sm = None
    if sm_id:
        active_sm = get_object_or_404(SocialMedia, pk=sm_id, is_active=True)
    elif social_medias:
        # Default to staff with unread or most recent message
        sms_with_msg = [s for s in social_medias if s.latest_message]
        if sms_with_msg:
            sms_with_msg.sort(key=lambda s: (s.unread_count > 0, s.latest_message.created_at), reverse=True)
            active_sm = sms_with_msg[0]
        else:
            active_sm = social_medias[0]

    chat_messages = []
    if active_sm:
        sm_status = active_sm.get_last_seen_info()
        active_sm.is_online = sm_status['is_online']
        active_sm.last_seen_text = sm_status['text']

        # Mark unread messages from this Social Media as read
        DeskSocialChatMessage.objects.filter(
            desk=desk,
            social_media=active_sm,
            sender_type='social_media',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskSocialChatMessage.objects.filter(
            desk=desk,
            social_media=active_sm
        ).order_by('created_at')

    context = {
        'active_page': 'desk_chat_social_media',
        'desk_user': desk,
        'social_medias': social_medias,
        'active_sm': active_sm,
        'chat_messages': chat_messages,
    }
    return render(request, 'desk/chat_social_media.html', context)


@desk_required
def desk_send_social_media_chat_message_view(request, sm_id):
    """
    POST/AJAX endpoint for Desk to send a message to Social Media staff.
    """
    _ensure_social_media_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Desk profile not found.'}, status=403)

    active_sm = get_object_or_404(SocialMedia, pk=sm_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskSocialChatMessage.objects.create(
        desk=desk,
        social_media=active_sm,
        sender_type='desk',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': desk.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('desk_chat_social_media_with_sm', sm_id=active_sm.pk)


@desk_required
def desk_get_social_media_chat_messages_api(request, sm_id):
    """
    GET AJAX polling endpoint for Desk chatting with Social Media staff.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Social Media as read.
    """
    _ensure_social_media_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_sm = get_object_or_404(SocialMedia, pk=sm_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskSocialChatMessage.objects.filter(
        desk=desk,
        social_media=active_sm,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='social_media', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskSocialChatMessage.objects.filter(
        desk=desk,
        sender_type='social_media',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': desk.name if m.sender_type == 'desk' else active_sm.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': m.created_at.strftime('%I:%M %p'),
            'date_formatted': m.created_at.strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    active_sm.refresh_from_db(fields=['last_seen'])
    sm_status = active_sm.get_last_seen_info()

    read_message_ids = list(DeskSocialChatMessage.objects.filter(
        desk=desk,
        social_media=active_sm,
        sender_type='desk',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': sm_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Desk <-> Reporter Chat Views
# ==========================================
@desk_required
def desk_chat_reporter_view(request, reporter_id=None):
    """
    Chat portal for Desk staff to communicate directly with Reporters.
    Lists all Reporters, shows unread message counts, latest message preview,
    and opens the conversation thread.
    """
    _ensure_reporter_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        messages.error(request, "No Desk profile found for this user account.")
        return redirect('desk_dashboard')

    reporters = list(Reporter.objects.filter(is_active=True).order_by('name'))

    for rep in reporters:
        rep_status = rep.get_last_seen_info()
        rep.is_online = rep_status['is_online']
        rep.last_seen_text = rep_status['text']
        rep.unread_count = DeskReporterChatMessage.objects.filter(
            desk=desk,
            reporter=rep,
            sender_type='reporter',
            is_read=False
        ).count()
        latest_msg = DeskReporterChatMessage.objects.filter(
            desk=desk,
            reporter=rep
        ).order_by('-created_at').first()
        rep.latest_message = latest_msg

    active_reporter = None
    if reporter_id:
        active_reporter = get_object_or_404(Reporter, pk=reporter_id, is_active=True)
    elif reporters:
        # Default to reporter with unread or most recent message
        reps_with_msg = [r for r in reporters if r.latest_message]
        if reps_with_msg:
            reps_with_msg.sort(key=lambda r: (r.unread_count > 0, r.latest_message.created_at), reverse=True)
            active_reporter = reps_with_msg[0]
        else:
            active_reporter = reporters[0]

    chat_messages = []
    if active_reporter:
        rep_status = active_reporter.get_last_seen_info()
        active_reporter.is_online = rep_status['is_online']
        active_reporter.last_seen_text = rep_status['text']

        # Mark unread messages from this Reporter as read
        DeskReporterChatMessage.objects.filter(
            desk=desk,
            reporter=active_reporter,
            sender_type='reporter',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskReporterChatMessage.objects.filter(
            desk=desk,
            reporter=active_reporter
        ).order_by('created_at')

    context = {
        'active_page': 'desk_chat_reporter',
        'desk_user': desk,
        'reporters': reporters,
        'active_reporter': active_reporter,
        'chat_messages': chat_messages,
    }
    return render(request, 'desk/chat_reporter.html', context)


@desk_required
def desk_send_reporter_chat_message_view(request, reporter_id):
    """
    POST/AJAX endpoint for Desk to send a message to a Reporter.
    """
    _ensure_reporter_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Desk profile not found.'}, status=403)

    active_reporter = get_object_or_404(Reporter, pk=reporter_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskReporterChatMessage.objects.create(
        desk=desk,
        reporter=active_reporter,
        sender_type='desk',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': desk.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('desk_chat_reporter_with_reporter', reporter_id=active_reporter.pk)


@desk_required
def desk_get_reporter_chat_messages_api(request, reporter_id):
    """
    GET AJAX polling endpoint for Desk chatting with Reporter.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Reporter as read.
    """
    _ensure_reporter_chat_table()
    desk = getattr(request.user, 'desk_profile', None)
    if not desk:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_reporter = get_object_or_404(Reporter, pk=reporter_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskReporterChatMessage.objects.filter(
        desk=desk,
        reporter=active_reporter,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='reporter', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskReporterChatMessage.objects.filter(
        desk=desk,
        sender_type='reporter',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': desk.name if m.sender_type == 'desk' else active_reporter.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': timezone.localtime(m.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(m.created_at).strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    Desk.objects.filter(pk=desk.pk).update(last_seen=timezone.now())

    active_reporter.refresh_from_db()
    rep_status = active_reporter.get_last_seen_info()

    read_message_ids = list(DeskReporterChatMessage.objects.filter(
        desk=desk,
        reporter=active_reporter,
        sender_type='desk',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': rep_status,
        'read_message_ids': read_message_ids,
    })


@login_required
def desk_assign_story_view(request, pk):
    """
    Handles assignment of a news story from Desk to:
    - Social Media Desk (with broadcast-ready edited video)
    - Graphic Designer
    - Voice Over
    - Visual Editor
    - Copy Editor
    """
    news = get_object_or_404(News, pk=pk)
    next_url = request.POST.get('next') or 'desk_my_work_list'

    if request.method != 'POST':
        return redirect(next_url)

    action = request.POST.get('action', '').strip()  # 'send_team' or 'send_social_media'
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'
    social_media_id = request.POST.get('social_media_id')
    desk_notes = request.POST.get('desk_notes', '').strip()

    # Route 1: Dispatched to Social Media
    # (Triggered when action is 'send_social_media', OR if video was finalized by Desk, OR if Social Media was selected)
    if action == 'send_social_media' or ((news.is_video_edited_by_desk or news.has_edited_video) and action == 'send_team') or (action == 'send_team' and social_media_id and not any([request.POST.get('graphic_designer_id'), request.POST.get('voice_over_id'), request.POST.get('visual_editor_id'), request.POST.get('copy_editor_id')])):
        if social_media_id:
            try:
                sm = SocialMedia.objects.get(pk=social_media_id, is_active=True)
                news.assigned_social_media = sm
            except (SocialMedia.DoesNotExist, ValueError):
                pass

        news.sent_to_social_media = True
        news.sent_to_social_media_at = timezone.now()
        if desk_notes:
            news.desk_notes = desk_notes
        news.save()

        assigned_target = f"Social Media Desk ({news.assigned_social_media.name})" if news.assigned_social_media else "Social Media team"
        msg = f'Broadcast video for "{news.headline}" has been successfully forwarded to {assigned_target}!'
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg, 'sent_to_social_media': True})
        messages.success(request, msg)
        return redirect(next_url)

    elif action == 'send_team':
        graphic_designer_id = request.POST.get('graphic_designer_id')
        voice_over_id = request.POST.get('voice_over_id')
        visual_editor_id = request.POST.get('visual_editor_id')
        copy_editor_id = request.POST.get('copy_editor_id')

        assigned_list = []

        # Social Media
        if social_media_id:
            try:
                sm = SocialMedia.objects.get(pk=social_media_id, is_active=True)
                news.assigned_social_media = sm
                news.sent_to_social_media = True
                news.sent_to_social_media_at = timezone.now()
                assigned_list.append(f"Social Media ({sm.name})")
            except (SocialMedia.DoesNotExist, ValueError):
                news.assigned_social_media = None

        # Graphic Designer
        if graphic_designer_id:
            try:
                gd = GraphicDesigner.objects.get(pk=graphic_designer_id, is_active=True)
                news.assigned_graphic_designer = gd
                assigned_list.append(f"Graphic Designer ({gd.name})")
            except (GraphicDesigner.DoesNotExist, ValueError):
                news.assigned_graphic_designer = None
        else:
            news.assigned_graphic_designer = None

        # Voice Over
        if voice_over_id:
            try:
                vo = VoiceOverUser.objects.get(pk=voice_over_id, is_active=True)
                news.assigned_voice_over = vo
                assigned_list.append(f"Voice Over ({vo.name})")
            except (VoiceOverUser.DoesNotExist, ValueError):
                news.assigned_voice_over = None
        else:
            news.assigned_voice_over = None

        # Visual Editor
        if visual_editor_id:
            try:
                ve = VisualEditor.objects.get(pk=visual_editor_id, is_active=True)
                news.assigned_visual_editor = ve
                assigned_list.append(f"Visual Editor ({ve.name})")
            except (VisualEditor.DoesNotExist, ValueError):
                news.assigned_visual_editor = None
        else:
            news.assigned_visual_editor = None

        # Copy Editor
        if copy_editor_id:
            try:
                ce = CopyEditor.objects.get(pk=copy_editor_id, is_active=True)
                news.assigned_copy_editor = ce
                news.is_script_edited_by_copy_editor = False
                assigned_list.append(f"Copy Editor ({ce.name})")
            except (CopyEditor.DoesNotExist, ValueError):
                news.assigned_copy_editor = None
        else:
            news.assigned_copy_editor = None

        news.desk_notes = desk_notes
        news.assigned_at = timezone.now()
        news.save()

        if assigned_list:
            msg = f'Story "{news.headline}" forwarded to: ' + ", ".join(assigned_list) + "."
        else:
            msg = f'Story "{news.headline}" updated.'

        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect(next_url)

    else:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        messages.error(request, "Invalid action selected.")
        return redirect('desk_my_word')


@login_required
def visual_editor_studio_view(request, pk):
    """
    In-Browser News Video Editor Studio.
    Accessible to Desk staff, Visual Editors, and central Admins.
    Provides 16:9 Live Preview Canvas, Aston Band headline overlays,
    scrolling ticker, reporter ID tags, trim in/out handles, and client-side rendering.
    """
    news = get_object_or_404(News, pk=pk)

    if is_desk_user(request.user):
        back_url = '/desk/my-work/'
        user_role = 'Desk Staff'
    elif hasattr(request.user, 'visual_editor_profile'):
        back_url = '/visual-editor/dashboard/'
        user_role = 'Visual Editor'
    else:
        back_url = f'/news/view/{news.pk}/'
        user_role = 'Editorial / Admin'

    # Collect all footage / media associated with story
    all_media = []
    if news.media_file:
        all_media.append({
            'url': news.media_file.url,
            'name': 'Primary Field Footage',
            'is_video': news.is_video,
            'is_image': news.is_image
        })

    for m in news.additional_media.all():
        if m.file:
            all_media.append({
                'url': m.file.url,
                'name': m.caption or f'Additional Media #{m.pk}',
                'is_video': m.is_video,
                'is_image': m.is_image
            })

    byte_file_url = news.byte_media.url if news.byte_media else None

    context = {
        'news': news,
        'all_media': all_media,
        'byte_file_url': byte_file_url,
        'back_url': back_url,
        'user_role': user_role,
        'is_desk': is_desk_user(request.user),
    }
    return render(request, 'visual_editor/studio.html', context)


@login_required
def save_edited_video_view(request, pk):
    """
    Receives the rendered video file from the In-Browser Studio via AJAX FormData,
    saves it to news.edited_video, marks is_video_edited_by_desk if saved by Desk,
    and updates the database.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST request required.'}, status=405)

    news = get_object_or_404(News, pk=pk)
    video_file = request.FILES.get('video_file')

    if not video_file or video_file.size == 0:
        return JsonResponse({'success': False, 'error': 'Video recording produced 0 bytes. Please try rendering again.'}, status=400)

    try:
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        clean_ext = '.mp4' if video_file.name.endswith('.mp4') else '.webm'
        clean_name = f"broadcast_news_{news.pk}_{timestamp}{clean_ext}"

        if news.edited_video:
            try:
                news.edited_video.delete(save=False)
            except Exception:
                pass

        news.edited_video.save(clean_name, video_file, save=False)
        news.edited_at = timezone.now()

        # If saved by Desk, mark is_video_edited_by_desk
        if is_desk_user(request.user):
            news.is_video_edited_by_desk = True

        # Optional auto-dispatch to Social Media
        if request.POST.get('dispatch_to_social_media') == '1':
            news.sent_to_social_media = True
            news.sent_to_social_media_at = timezone.now()

        news.save()

        return JsonResponse({
            'success': True,
            'message': 'Broadcast news video rendered and saved successfully!',
            'video_url': news.edited_video.url,
            'video_size': news.edited_video.size,
            'is_video_edited_by_desk': news.is_video_edited_by_desk,
            'sent_to_social_media': news.sent_to_social_media
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



# ==========================================
# Social Media Portal Views (Social Media Staff Access)
# ==========================================
@social_media_required
def social_media_dashboard_view(request):
    """
    Social Media Staff Personal Dashboard.
    """
    sm = request.user.social_media_profile
    total_approved = News.objects.filter(status='Approved').count()
    total_news = News.objects.count()
    active_reporters = Reporter.objects.filter(is_active=True).count()
    my_tasks = News.objects.select_related('reporter', 'author').filter(
        Q(sent_to_social_media=True) | Q(is_video_edited_by_desk=True)
    ).order_by('-sent_to_social_media_at', '-created_at')
    my_tasks_count = my_tasks.count()

    context = {
        'active_page': 'social_media_dashboard',
        'social_media': sm,
        'total_approved': total_approved,
        'total_news': total_news,
        'active_reporters': active_reporters,
        'my_tasks_count': my_tasks_count,
        'recent_tasks': my_tasks[:6],
    }
    return render(request, 'social_media/dashboard.html', context)


@social_media_required
def social_media_my_task_view(request):
    """
    Social Media Staff 'My Task' Portal:
    Displays all news stories dispatched by Desk to Social Media.
    Highlights stories with broadcast-ready edited videos, script, and images.
    """
    sm = request.user.social_media_profile
    tasks = News.objects.select_related('reporter', 'author').prefetch_related('additional_media').filter(
        Q(sent_to_social_media=True) | Q(is_video_edited_by_desk=True)
    ).order_by('-sent_to_social_media_at', '-created_at')

    query = request.GET.get('q', '').strip()
    if query:
        tasks = tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query)
        )

    context = {
        'active_page': 'social_media_my_task',
        'social_media': sm,
        'tasks': tasks,
        'tasks_count': tasks.count(),
        'query': query,
    }
    return render(request, 'social_media/my_task.html', context)


@social_media_required
def social_media_profile_view(request):
    """
    Social Media Staff Profile View.
    """
    sm = request.user.social_media_profile
    context = {
        'active_page': 'social_media_profile',
        'social_media': sm,
    }
    return render(request, 'social_media/profile.html', context)


# ==========================================
# Social Media <-> Desk Chat Views
# ==========================================
@social_media_required
def social_media_chat_desk_view(request, desk_id=None):
    """
    Chat portal for Social Media staff to communicate directly with Desk staff.
    Lists all Desk staff, shows unread messages from Desk, and opens conversation thread.
    """
    _ensure_social_media_chat_table()
    sm = getattr(request.user, 'social_media_profile', None)
    if not sm:
        messages.error(request, "No Social Media profile found.")
        return redirect('social_media_dashboard')

    desks = list(Desk.objects.filter(is_active=True).order_by('name'))

    for d in desks:
        d_status = d.get_last_seen_info()
        d.is_online = d_status['is_online']
        d.last_seen_text = d_status['text']
        d.unread_count = DeskSocialChatMessage.objects.filter(
            desk=d,
            social_media=sm,
            sender_type='desk',
            is_read=False
        ).count()
        latest_msg = DeskSocialChatMessage.objects.filter(
            desk=d,
            social_media=sm
        ).order_by('-created_at').first()
        d.latest_message = latest_msg

    active_desk = None
    if desk_id:
        active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    elif desks:
        # Default to Desk with unread or most recent message
        desks_with_msg = [d for d in desks if d.latest_message]
        if desks_with_msg:
            desks_with_msg.sort(key=lambda d: (d.unread_count > 0, d.latest_message.created_at), reverse=True)
            active_desk = desks_with_msg[0]
        else:
            active_desk = desks[0]

    chat_messages = []
    if active_desk:
        desk_status = active_desk.get_last_seen_info()
        active_desk.is_online = desk_status['is_online']
        active_desk.last_seen_text = desk_status['text']

        # Mark unread messages from this Desk as read
        DeskSocialChatMessage.objects.filter(
            desk=active_desk,
            social_media=sm,
            sender_type='desk',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskSocialChatMessage.objects.filter(
            desk=active_desk,
            social_media=sm
        ).order_by('created_at')

    context = {
        'active_page': 'social_media_chat_desk',
        'social_media': sm,
        'desks': desks,
        'active_desk': active_desk,
        'chat_messages': chat_messages,
    }
    return render(request, 'social_media/chat_desk.html', context)


@social_media_required
def social_media_send_chat_message_view(request, desk_id):
    """
    POST/AJAX endpoint for Social Media staff to send a message to Desk.
    """
    _ensure_social_media_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    sm = getattr(request.user, 'social_media_profile', None)
    if not sm:
        return JsonResponse({'success': False, 'error': 'Social Media profile not found.'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskSocialChatMessage.objects.create(
        desk=active_desk,
        social_media=sm,
        sender_type='social_media',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    SocialMedia.objects.filter(pk=sm.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': sm.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('social_media_chat_desk_with_desk', desk_id=active_desk.pk)


@social_media_required
def social_media_get_chat_messages_api(request, desk_id):
    """
    GET AJAX polling endpoint for Social Media staff.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Desk as read.
    """
    _ensure_social_media_chat_table()
    sm = getattr(request.user, 'social_media_profile', None)
    if not sm:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskSocialChatMessage.objects.filter(
        desk=active_desk,
        social_media=sm,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='desk', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskSocialChatMessage.objects.filter(
        social_media=sm,
        sender_type='desk',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': active_desk.name if m.sender_type == 'desk' else sm.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': timezone.localtime(m.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(m.created_at).strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    SocialMedia.objects.filter(pk=sm.pk).update(last_seen=timezone.now())

    active_desk.refresh_from_db(fields=['last_seen'])
    desk_status = active_desk.get_last_seen_info()

    read_message_ids = list(DeskSocialChatMessage.objects.filter(
        desk=active_desk,
        social_media=sm,
        sender_type='social_media',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': desk_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Graphic Designer Portal Views (Graphic Designer Staff Access)
# ==========================================
def _ensure_graphic_designer_columns():
    pass


@graphic_designer_required
def graphic_designer_dashboard_view(request):
    """
    Graphic Designer Staff Personal Dashboard.
    """
    _ensure_graphic_designer_columns()
    designer = request.user.graphic_designer_profile
    total_approved = News.objects.filter(status='Approved').count()
    total_news = News.objects.count()
    active_reporters = Reporter.objects.filter(is_active=True).count()
    all_tasks = News.objects.select_related('reporter', 'author').filter(
        assigned_graphic_designer=designer
    ).order_by('-assigned_at', '-created_at')
    pending_tasks = all_tasks.filter(is_graphics_completed=False)
    completed_tasks = all_tasks.filter(is_graphics_completed=True)

    context = {
        'active_page': 'graphic_designer_dashboard',
        'designer': designer,
        'total_approved': total_approved,
        'total_news': total_news,
        'active_reporters': active_reporters,
        'my_tasks_count': pending_tasks.count(),
        'pending_count': pending_tasks.count(),
        'completed_count': completed_tasks.count(),
        'recent_tasks': pending_tasks[:6],
    }
    return render(request, 'graphic_designer/dashboard.html', context)


@graphic_designer_required
def graphic_designer_my_task_view(request):
    """
    Graphic Designer Staff 'My Task' Portal:
    Displays pending stories assigned to this Graphic Designer by Desk that need creatives/artwork.
    Once graphics are ready, clicking 'Send to Visual Editor' moves them to 'My Work List'.
    """
    _ensure_graphic_designer_columns()
    _ensure_copy_editor_columns()
    designer = request.user.graphic_designer_profile
    all_assigned = News.objects.select_related(
        'reporter', 'author',
        'assigned_visual_editor', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer', 'assigned_voice_over'
    ).prefetch_related('additional_media').filter(
        assigned_graphic_designer=designer
    ).order_by('-assigned_at', '-created_at')

    # Pending tasks: graphics have not yet been marked completed / sent to Visual Editor
    pending_tasks = all_assigned.filter(is_graphics_completed=False)
    completed_count = all_assigned.filter(is_graphics_completed=True).count()
    pending_count = pending_tasks.count()

    query = request.GET.get('q', '').strip()
    if query:
        pending_tasks = pending_tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query) |
            Q(category__icontains=query)
        )

    visual_editors = VisualEditor.objects.filter(is_active=True).order_by('name')

    context = {
        'active_page': 'graphic_designer_my_task',
        'designer': designer,
        'tasks': pending_tasks,
        'tasks_count': pending_tasks.count(),
        'pending_count': pending_count,
        'completed_count': completed_count,
        'visual_editors': visual_editors,
        'query': query,
    }
    return render(request, 'graphic_designer/my_task.html', context)


@graphic_designer_required
def graphic_designer_my_work_list_view(request):
    """
    Graphic Designer Staff 'My Work List' Portal:
    Displays all stories where graphics have been completed and dispatched to Visual Editor.
    """
    _ensure_graphic_designer_columns()
    _ensure_copy_editor_columns()
    designer = request.user.graphic_designer_profile
    all_assigned = News.objects.select_related(
        'reporter', 'author',
        'assigned_visual_editor', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer', 'assigned_voice_over'
    ).prefetch_related('additional_media').filter(
        assigned_graphic_designer=designer
    ).order_by('-graphics_sent_to_visual_editor_at', '-assigned_at', '-created_at')

    completed_tasks = all_assigned.filter(is_graphics_completed=True)
    pending_count = all_assigned.filter(is_graphics_completed=False).count()
    completed_count = completed_tasks.count()

    query = request.GET.get('q', '').strip()
    if query:
        completed_tasks = completed_tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query) |
            Q(category__icontains=query)
        )

    context = {
        'active_page': 'graphic_designer_my_work_list',
        'designer': designer,
        'tasks': completed_tasks,
        'tasks_count': completed_tasks.count(),
        'pending_count': pending_count,
        'completed_count': completed_count,
        'query': query,
    }
    return render(request, 'graphic_designer/my_work_list.html', context)


@graphic_designer_required
def graphic_designer_send_to_visual_editor_view(request, pk):
    """
    Mark story graphics as completed and forward to Visual Editor.
    Story moves automatically from 'My Task' to 'My Work List'.
    """
    _ensure_graphic_designer_columns()
    news = get_object_or_404(News, pk=pk)
    designer = request.user.graphic_designer_profile

    if news.assigned_graphic_designer != designer and not is_admin_user(request.user):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        messages.error(request, 'Permission denied for this story.')
        return redirect('graphic_designer_my_task')

    if request.method == 'POST':
        ve_id = request.POST.get('visual_editor_id')
        if ve_id:
            try:
                ve = VisualEditor.objects.get(pk=ve_id, is_active=True)
                news.assigned_visual_editor = ve
            except VisualEditor.DoesNotExist:
                pass

        instructions = request.POST.get('instructions', '').strip()
        if instructions:
            existing = news.desk_notes or ""
            news.desk_notes = f"{existing}\n[Graphics Note]: {instructions}".strip()

        news.is_graphics_completed = True
        news.graphics_sent_to_visual_editor_at = timezone.now()
        news.save()

        ve_display = news.assigned_visual_editor.name if news.assigned_visual_editor else "Visual Editor Desk"
        msg = f'Graphics for "{news.headline[:40]}..." sent to Visual Editor ({ve_display})! Story moved to My Work List.'

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({
                'success': True,
                'message': msg,
                'redirect_url': '/graphic-designer/my-work-list/'
            })

        messages.success(request, msg)
        return redirect('graphic_designer_my_work_list')

    return redirect('graphic_designer_my_task')


@graphic_designer_required
def graphic_designer_recall_task_view(request, pk):
    """
    Recall a story from My Work List back to My Task (e.g. to update or add graphics).
    """
    _ensure_graphic_designer_columns()
    news = get_object_or_404(News, pk=pk)
    designer = request.user.graphic_designer_profile

    if news.assigned_graphic_designer != designer and not is_admin_user(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('graphic_designer_my_work_list')

    news.is_graphics_completed = False
    news.save()
    messages.info(request, f'Story "{news.headline[:40]}..." recalled back to My Task for editing graphics.')
    return redirect('graphic_designer_my_task')


@graphic_designer_required
def graphic_designer_upload_graphics_view(request, pk):
    """
    Upload creative graphics, social banners, thumbnails, or Aston lower-thirds for an assigned story.
    Creates NewsMedia items associated with the story.
    """
    news = get_object_or_404(News, pk=pk)
    designer = request.user.graphic_designer_profile

    if news.assigned_graphic_designer != designer and not is_admin_user(request.user):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        messages.error(request, 'Permission denied for this story.')
        return redirect('graphic_designer_my_task')

    if request.method == 'POST':
        files = request.FILES.getlist('graphic_files')
        single_file = request.FILES.get('graphic_file')
        if single_file and not files:
            files = [single_file]

        if not files:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                return JsonResponse({'success': False, 'error': 'Please select at least one graphic file to upload.'}, status=400)
            messages.error(request, 'Please select at least one graphic file to upload.')
            return redirect('graphic_designer_my_task')

        asset_type = request.POST.get('asset_type', '').strip()
        custom_caption = request.POST.get('caption', '').strip()
        caption_text = custom_caption or asset_type or 'Graphic Asset'

        uploaded_items = []
        for f in files:
            media_item = NewsMedia.objects.create(
                news=news,
                file=f,
                caption=caption_text
            )
            uploaded_items.append({
                'id': media_item.pk,
                'url': media_item.file.url,
                'name': media_item.caption,
                'is_image': media_item.is_image
            })

        count = len(uploaded_items)
        msg = f'Successfully uploaded {count} creative graphic asset{"s" if count > 1 else ""} for "{news.headline[:40]}..."!'

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({
                'success': True,
                'message': msg,
                'count': count,
                'uploaded': uploaded_items
            })

        messages.success(request, msg)
        return redirect('graphic_designer_my_task')

    return redirect('graphic_designer_my_task')


@graphic_designer_required
def graphic_designer_delete_media_view(request, pk):
    """
    Delete an uploaded creative asset from a story.
    """
    media_item = get_object_or_404(NewsMedia, pk=pk)
    news = media_item.news
    designer = request.user.graphic_designer_profile

    if news.assigned_graphic_designer != designer and not is_admin_user(request.user):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        messages.error(request, 'Permission denied.')
        return redirect('graphic_designer_my_task')

    try:
        media_item.file.delete(save=False)
    except Exception:
        pass
    media_item.delete()

    msg = 'Graphic asset removed successfully.'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': msg})

    messages.success(request, msg)
    return redirect('graphic_designer_my_task')


@graphic_designer_required
def graphic_designer_generate_ai_image_view(request):
    """
    Generate News Graphics / Artwork using AI.
    Translates regional (Odia/Hindi) prompts to English visual scene descriptions using Gemini,
    generates the image via AI image engines, downloads the image server-side,
    and returns a local media URL so preview and downloads NEVER break.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST request required.'}, status=405)

    import urllib.parse
    import random
    import time
    import requests
    import re
    from django.conf import settings
    from .ai_service import (
        get_api_key, call_gemini, analyze_reference_image_for_prompt,
        free_translate_to_english, generate_image_with_gemini
    )

    try:
        if request.content_type == 'application/json' and request.body:
            import json
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        prompt = data.get('prompt', '').strip()
        aspect_ratio = data.get('aspect_ratio', '16:9').strip()
        style = data.get('style', 'photorealistic news').strip()
        headline = data.get('headline', '').strip()
        reference_image_url = data.get('reference_image_url', '').strip()

        # Handle Reference Image (either uploaded file from PC or story media URL)
        ref_image_file = request.FILES.get('reference_image')
        ref_image_bytes = None
        ref_mime_type = 'image/jpeg'

        if ref_image_file:
            ref_image_bytes = ref_image_file.read()
            ref_mime_type = ref_image_file.content_type or 'image/jpeg'
        elif reference_image_url:
            if reference_image_url.startswith(settings.MEDIA_URL):
                rel_p = reference_image_url[len(settings.MEDIA_URL):]
                disk_p = os.path.join(settings.MEDIA_ROOT, rel_p.replace('/', os.sep))
                if os.path.exists(disk_p):
                    try:
                        with open(disk_p, 'rb') as f:
                            ref_image_bytes = f.read()
                        if disk_p.lower().endswith('.png'):
                            ref_mime_type = 'image/png'
                        elif disk_p.lower().endswith('.webp'):
                            ref_mime_type = 'image/webp'
                    except Exception:
                        pass
            elif reference_image_url.startswith(('http://', 'https://')):
                try:
                    r = requests.get(reference_image_url, timeout=10)
                    if r.status_code == 200:
                        ref_image_bytes = r.content
                        ref_mime_type = r.headers.get('content-type', 'image/jpeg')
                except Exception:
                    pass

        if not prompt and not ref_image_bytes:
            return JsonResponse({'success': False, 'error': 'Please enter a prompt or provide a reference image.'}, status=400)

        # 1. Visual Prompt Generation: Multimodal (if reference image provided) OR Regional Translation (Hindi/Odia/Hinglish)
        english_prompt = prompt or headline or "Indian television news broadcast report, live coverage still"
        reference_analyzed = False

        if ref_image_bytes:
            # Multimodal Vision Analysis: Reference image + Hindi/Odia/English prompt
            try:
                analyzed_vision_prompt = analyze_reference_image_for_prompt(
                    image_bytes=ref_image_bytes,
                    user_prompt=prompt or headline or "create realistic TV news graphic based on this photo",
                    style=style,
                    headline=headline,
                    mime_type=ref_mime_type
                )
                if analyzed_vision_prompt and len(analyzed_vision_prompt.strip()) > 5:
                    clean_vision = re.sub(r'[\r\n"\'`]+', ' ', analyzed_vision_prompt).strip()
                    if clean_vision:
                        english_prompt = clean_vision
                        reference_analyzed = True
            except Exception as e:
                pass

        if not reference_analyzed and prompt:
            # Translate regional prompt (Odia, Hindi, Hinglish) to accurate English
            has_non_ascii = any(ord(c) > 127 for c in prompt)
            translated_candidate = prompt
            if has_non_ascii:
                translated_candidate = free_translate_to_english(prompt)

            # Try Gemini for broadcast visual enhancement
            try:
                gemini_key = get_api_key('gemini')
                if gemini_key:
                    translate_prompt = (
                        "You are an expert news visual designer for an Indian television news channel (Prameya Digital).\n"
                        "Convert this news headline/prompt into a vivid, realistic English visual scene description "
                        "for generating a high-definition news broadcast photo or graphic asset.\n"
                        "Describe the subjects, their attire, facial expressions, and broadcast studio or event scene realistically.\n"
                        "Output ONLY the concise visual description (under 30 words), with no quotes, markdown, or preface.\n\n"
                        f"News Headline/Prompt: {translated_candidate}"
                    )
                    translated = call_gemini(translate_prompt, gemini_key)
                    if translated and len(translated.strip()) > 3:
                        clean_translated = re.sub(r'[\r\n"\'`]+', ' ', translated).strip()
                        if clean_translated:
                            english_prompt = clean_translated
                else:
                    english_prompt = translated_candidate
            except Exception:
                english_prompt = translated_candidate

        # Ensure no residual non-ascii chars break downstream image engines
        if any(ord(c) > 127 for c in english_prompt):
            english_prompt = free_translate_to_english(english_prompt)
            if any(ord(c) > 127 for c in english_prompt):
                english_prompt = "".join([c for c in english_prompt if ord(c) < 128]).strip() or "Indian television news broadcast report, live coverage still"

        # Style enhancements tailored for TV News & Media
        style_prompts = {
            'photorealistic news': 'photorealistic news broadcast still, authentic journalism photo, sharp focus, 8k resolution, crisp detail',
            'breaking news': 'dramatic TV news breaking news graphic banner, television news studio backdrop, vibrant colors, professional broadcast art',
            '3d render': 'modern 3D isometric render, ultra-detailed, vibrant studio lighting, polished graphic design for digital media',
            'vector art': 'clean minimalist flat vector graphic illustration, editorial magazine cover style, bold typography layout, sharp lines',
            'cinematic': 'cinematic 35mm film photography, atmospheric lighting, depth of field, dramatic news story scene'
        }
        style_suffix = style_prompts.get(style, style_prompts['photorealistic news'])

        # Aspect ratio mapping
        if aspect_ratio == '1:1':
            width, height = 1024, 1024
        elif aspect_ratio == '9:16':
            width, height = 720, 1280
        else:  # 16:9
            width, height = 1280, 720

        enhanced_prompt = f"{english_prompt}, {style_suffix}, high quality, clean composition, no watermark"
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        seed = random.randint(10000, 9999999)

        img_bytes = None

        # Step 2A: Try Google Gemini Native Image Generation
        try:
            gemini_key = get_api_key('gemini')
            if gemini_key:
                gemini_img = generate_image_with_gemini(
                    prompt=f"{enhanced_prompt}. Wide angle, professional broadcast graphics, photorealistic 8k.",
                    reference_image_bytes=ref_image_bytes,
                    mime_type=ref_mime_type,
                    api_key=gemini_key
                )
                if gemini_img and len(gemini_img) > 1000:
                    img_bytes = gemini_img
        except Exception:
            pass

        # Step 2B: Fallback to high-end FLUX / Pollinations models
        if not img_bytes:
            candidate_urls = []
            # Unified Gen endpoint
            candidate_urls.append(
                f"https://gen.pollinations.ai/image/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
            )
            # Reference image URL parameter if available
            if reference_image_url and reference_image_url.startswith(('http://', 'https://')):
                candidate_urls.append(
                    f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&image={urllib.parse.quote(reference_image_url)}&model=flux&seed={seed}&nologo=true"
                )
            candidate_urls.extend([
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&seed={seed}&nologo=true",
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=turbo&seed={seed}&nologo=true",
                f"https://image.pollinations.ai/prompt/{urllib.parse.quote(english_prompt)}?width={width}&height={height}&nologo=true"
            ])

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            for test_url in candidate_urls:
                try:
                    resp = requests.get(test_url, headers=headers, timeout=25)
                    if resp.status_code == 200 and resp.content and len(resp.content) > 1000:
                        content_type = resp.headers.get('content-type', '').lower()
                        if 'image' in content_type or resp.content[:4] in (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\x89PNG', b'RIFF'):
                            img_bytes = resp.content
                            break
                except Exception:
                    continue

        if not img_bytes:
            # Fallback attempt
            fallback_encoded = urllib.parse.quote("Indian TV news studio live broadcast reporting breaking news 4k")
            try:
                resp = requests.get(f"https://image.pollinations.ai/prompt/{fallback_encoded}?width={width}&height={height}&seed={seed}&nologo=true", headers=headers, timeout=15)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    img_bytes = resp.content
            except Exception:
                pass

        if not img_bytes:
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (width, height), color=(15, 23, 42))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (width, int(height * 0.12))], fill=(219, 39, 119))
                draw.rectangle([(0, int(height * 0.78)), (width, height)], fill=(15, 23, 42))
                draw.rectangle([(0, int(height * 0.75)), (width, int(height * 0.78))], fill=(225, 29, 72))
                import io
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=90)
                img_bytes = buf.getvalue()
            except Exception:
                pass

        if not img_bytes:
            return JsonResponse({'success': False, 'error': 'AI Image generation timed out. Please try clicking "Generate Artwork with AI" again.'}, status=504)

        # Save to media folder locally so it never fails to preview or download
        media_subpath = 'news_media'
        full_dir = os.path.join(settings.MEDIA_ROOT, media_subpath)
        os.makedirs(full_dir, exist_ok=True)

        filename = f"ai_gen_{int(time.time())}_{random.randint(1000, 9999)}.jpg"
        file_path = os.path.join(full_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(img_bytes)

        local_url = f"{settings.MEDIA_URL}{media_subpath}/{filename}"
        relative_path = f"{media_subpath}/{filename}"

        return JsonResponse({
            'success': True,
            'image_url': local_url,
            'relative_path': relative_path,
            'filename': filename,
            'prompt': prompt,
            'english_prompt': english_prompt,
            'reference_used': bool(ref_image_bytes),
            'reference_analyzed': reference_analyzed,
            'aspect_ratio': aspect_ratio,
            'dimensions': f"{width}x{height}",
            'style': style
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'AI Generation Error: {str(e)}'}, status=500)


@graphic_designer_required
def graphic_designer_save_ai_image_to_story_view(request, pk):
    """
    Attaches the generated AI image directly as a NewsMedia asset for the story.
    Supports either pre-downloaded local relative_path (instantaneous) or external image_url.
    """
    news = get_object_or_404(News, pk=pk)
    designer = request.user.graphic_designer_profile

    if news.assigned_graphic_designer != designer and not is_admin_user(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required.'}, status=405)

    import os
    import requests
    from django.conf import settings
    from django.core.files.base import ContentFile

    try:
        if request.content_type == 'application/json' and request.body:
            import json
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        image_url = data.get('image_url', '').strip()
        relative_path = data.get('relative_path', '').strip()
        caption = data.get('caption', '').strip() or 'AI Generated Graphic Artwork'

        media_item = None

        # 1. First check if relative_path was passed and exists locally
        if relative_path:
            full_existing_path = os.path.join(settings.MEDIA_ROOT, relative_path.replace('/', os.sep))
            if os.path.exists(full_existing_path):
                media_item = NewsMedia.objects.create(
                    news=news,
                    file=relative_path,
                    caption=caption
                )

        # 2. Check if image_url is a local media URL (/media/...)
        if not media_item and image_url and image_url.startswith(settings.MEDIA_URL):
            clean_subpath = image_url[len(settings.MEDIA_URL):].lstrip('/')
            full_path = os.path.join(settings.MEDIA_ROOT, clean_subpath.replace('/', os.sep))
            if os.path.exists(full_path):
                media_item = NewsMedia.objects.create(
                    news=news,
                    file=clean_subpath,
                    caption=caption
                )

        # 3. Fallback: External provider URL
        if not media_item:
            if not image_url:
                return JsonResponse({'success': False, 'error': 'No image URL provided.'}, status=400)

            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(image_url, headers=headers, timeout=30)
            if resp.status_code != 200 or not resp.content:
                return JsonResponse({'success': False, 'error': f'Could not download image from provider (HTTP {resp.status_code}).'}, status=400)

            timestamp = int(timezone.now().timestamp())
            filename = f"ai_graphic_{news.pk}_{timestamp}.jpg"

            media_item = NewsMedia.objects.create(
                news=news,
                caption=caption
            )
            media_item.file.save(filename, ContentFile(resp.content), save=True)

        return JsonResponse({
            'success': True,
            'message': f'AI graphic saved directly to "{news.headline[:40]}..."!',
            'media': {
                'id': media_item.pk,
                'url': media_item.file.url,
                'caption': media_item.caption,
                'is_image': media_item.is_image
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Save failed: {str(e)}'}, status=500)


@graphic_designer_required
def graphic_designer_profile_view(request):
    """
    Graphic Designer Staff Profile View.
    """
    _ensure_graphic_designer_columns()
    designer = request.user.graphic_designer_profile
    all_assigned = News.objects.filter(assigned_graphic_designer=designer)
    pending_count = all_assigned.filter(is_graphics_completed=False).count()
    completed_count = all_assigned.filter(is_graphics_completed=True).count()
    context = {
        'active_page': 'graphic_designer_profile',
        'designer': designer,
        'pending_count': pending_count,
        'completed_count': completed_count,
    }
    return render(request, 'graphic_designer/profile.html', context)




# ==========================================
# Input Portal Views (Input Staff Access)
# ==========================================
@input_required
def input_dashboard_view(request):
    """
    Input Staff Personal Dashboard.
    Incoming raw field submissions from reporters arrive here first for verification!
    """
    input_user = request.user.input_profile
    total_approved = News.objects.filter(status='Approved').count()
    total_news = News.objects.count()
    active_reporters = Reporter.objects.filter(is_active=True).count()
    submitted_news = News.objects.filter(status='Submitted').count()
    # All incoming news waiting for Input verification
    pending_incoming_news = News.objects.select_related('reporter', 'author').filter(status='Submitted').order_by('-created_at')
    recent_news = News.objects.select_related('reporter', 'author').order_by('-created_at')[:8]

    context = {
        'active_page': 'input_dashboard',
        'input_user': input_user,
        'total_approved': total_approved,
        'total_news': total_news,
        'active_reporters': active_reporters,
        'submitted_news': submitted_news,
        'pending_incoming_news': pending_incoming_news,
        'recent_news': recent_news,
    }
    return render(request, 'input/dashboard.html', context)


@input_required
def input_profile_view(request):
    """
    Input Staff Profile View.
    """
    input_user = request.user.input_profile
    context = {
        'active_page': 'input_profile',
        'input_user': input_user,
    }
    return render(request, 'input/profile.html', context)


@login_required
def input_news_verify_list_view(request):
    """
    Input Desk - News Verification & Reporter Feed Workspace.
    Field reporters' raw incoming stories show here first.
    Input staff reviews the video, audio byte, and script, and can:
    - Approve / Select: story becomes Approved and is forwarded to Editorial Desk.
    - Reject: story is rejected and media is deleted from disk.
    """
    if is_reporter_user(request.user):
        messages.error(request, "Access restricted to Input Desk & Central Admins.")
        return redirect('reporter_dashboard')

    query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()
    category_filter = request.GET.get('category', '').strip()
    district_filter = request.GET.get('district', '').strip()
    status_filter = request.GET.get('status', '').strip()

    today_str = timezone.localdate().strftime('%Y-%m-%d')
    if 'date' in request.GET:
        selected_date = request.GET.get('date', '').strip()
    else:
        selected_date = today_str

    news_qs = News.objects.select_related('reporter', 'author').all()

    # Overall counts across all dates
    total_all_count = news_qs.count()
    approved_all_count = news_qs.filter(status='Approved').count()
    pending_all_count = news_qs.filter(status='Submitted').count()
    rejected_all_count = news_qs.filter(status='Rejected').count()

    # Apply date filter
    filter_date = None
    if selected_date and selected_date != 'all':
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            news_qs = news_qs.filter(created_at__date=filter_date)
        except ValueError:
            selected_date = ''

    # Filtered date counts
    if filter_date:
        date_qs = News.objects.filter(created_at__date=filter_date)
    else:
        date_qs = News.objects.all()

    date_total_count = date_qs.count()
    date_approved_count = date_qs.filter(status='Approved').count()
    date_pending_count = date_qs.filter(status='Submitted').count()
    date_rejected_count = date_qs.filter(status='Rejected').count()

    # Search & other filters
    if query:
        news_qs = news_qs.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(district__icontains=query) |
            Q(byte_interview__icontains=query) |
            Q(reporter__name__icontains=query) |
            Q(reporter__reporter_id__icontains=query) |
            Q(reporter__phone_number__icontains=query)
        )

    if type_filter:
        news_qs = news_qs.filter(news_type=type_filter)

    if category_filter:
        news_qs = news_qs.filter(category=category_filter)

    if district_filter:
        news_qs = news_qs.filter(district__iexact=district_filter)

    if status_filter:
        news_qs = news_qs.filter(status=status_filter)

    all_districts = News.objects.values_list('district', flat=True).distinct().order_by('district')
    if not all_districts:
        all_districts = Reporter.objects.values_list('district', flat=True).distinct().order_by('district')

    input_user = getattr(request.user, 'input_profile', None)

    context = {
        'active_page': 'news_verify_list',
        'news_list': news_qs,
        'selected_date': selected_date,
        'today_str': today_str,
        'date_total_count': date_total_count,
        'date_approved_count': date_approved_count,
        'date_pending_count': date_pending_count,
        'date_rejected_count': date_rejected_count,
        'total_all_count': total_all_count,
        'approved_all_count': approved_all_count,
        'pending_all_count': pending_all_count,
        'rejected_all_count': rejected_all_count,
        'query': query,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'district_filter': district_filter,
        'status_filter': status_filter,
        'all_districts': all_districts,
        'news_types': [c[0] for c in NEWS_TYPE_CHOICES],
        'news_categories': [c[0] for c in NEWS_CATEGORY_CHOICES],
        'input_user': input_user,
        'base_template': 'input/base_input.html',
        'is_input': True,
        'is_desk': False,
        'is_admin': is_admin_user(request.user),
        'status_update_url_name': 'input_update_news_status',
        'download_zip_url_name': 'input_download_approved_zip',
        'verify_list_url_name': 'input_news_verify_list',
    }
    return render(request, 'input/news_verify_list.html', context)


def generate_story_word_document(news, rep_name, rep_id, rep_phone):
    """
    Generates MS Word compatible HTML document content with full styling and Odia/Unicode support.
    """
    submission_time = news.created_at.strftime('%d %B, %Y  %I:%M %p') if news.created_at else 'N/A'
    byte_section = ""
    if news.byte_interview:
        byte_section = f"""
        <div style="font-size: 13pt; font-weight: bold; color: #0284c7; margin-top: 24px; margin-bottom: 8px; border-bottom: 1.5px solid #cbd5e1; padding-bottom: 4px;">
            BYTE / SOUNDBITE DETAILS &amp; TRANSCRIPT:
        </div>
        <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 14px 16px; font-size: 11pt; line-height: 1.6; color: #1e3a8a; white-space: pre-wrap;">
{news.byte_interview}
        </div>
        """

    return f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>{news.headline}</title>
<style>
  body {{ font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 11pt; color: #1e293b; line-height: 1.6; margin: 30px; }}
  .channel-header {{ border-bottom: 3px solid #0891b2; padding-bottom: 10px; margin-bottom: 20px; }}
  .channel-name {{ font-size: 22pt; font-weight: 800; color: #0891b2; margin: 0; letter-spacing: 0.5px; }}
  .channel-sub {{ font-size: 10.5pt; font-weight: 700; color: #64748b; margin-top: 4px; text-transform: uppercase; }}
  .headline-banner {{ background-color: #f0fdf4; border: 1.5px solid #86efac; border-left: 6px solid #10b981; padding: 14px 18px; margin: 18px 0; }}
  .headline-title {{ font-size: 16pt; font-weight: 800; color: #0f172a; margin: 0; }}
  .meta-table {{ width: 100%; border-collapse: collapse; margin: 18px 0; }}
  .meta-table td {{ border: 1px solid #cbd5e1; padding: 8px 12px; font-size: 10pt; }}
  .meta-table .label {{ background-color: #f8fafc; font-weight: bold; color: #475569; width: 22%; }}
  .meta-table .val {{ color: #0f172a; font-weight: 600; }}
  .section-title {{ font-size: 13pt; font-weight: bold; color: #0891b2; margin-top: 24px; margin-bottom: 8px; border-bottom: 1.5px solid #cbd5e1; padding-bottom: 4px; text-transform: uppercase; }}
  .script-box {{ background-color: #ffffff; border: 1px solid #e2e8f0; padding: 16px; font-size: 11.5pt; line-height: 1.8; color: #1e293b; white-space: pre-wrap; }}
  .footer-note {{ margin-top: 40px; border-top: 1px solid #cbd5e1; padding-top: 10px; font-size: 9pt; color: #94a3b8; text-align: center; }}
</style>
</head>
<body>
  <div class="channel-header">
    <div class="channel-name">PRAMEYA DIGITAL NEWS NETWORK</div>
    <div class="channel-sub">Verified Editorial &amp; Broadcast Package</div>
  </div>

  <div class="headline-banner">
    <h1 class="headline-title">{news.headline}</h1>
  </div>

  <table class="meta-table">
    <tr>
      <td class="label">Story ID:</td>
      <td class="val">NL-STORY-{news.pk:05d}</td>
      <td class="label">Status:</td>
      <td class="val" style="color: #059669; font-weight: bold;">{news.status} (Selected for Telecast)</td>
    </tr>
    <tr>
      <td class="label">News Format:</td>
      <td class="val">{news.news_type}</td>
      <td class="label">Category:</td>
      <td class="val">{news.category}</td>
    </tr>
    <tr>
      <td class="label">District:</td>
      <td class="val">{news.district}</td>
      <td class="label">Location / Beat:</td>
      <td class="val">{news.location}</td>
    </tr>
    <tr>
      <td class="label">Field Reporter:</td>
      <td class="val">{rep_name} (ID: {rep_id})</td>
      <td class="label">Reporter Contact:</td>
      <td class="val">{rep_phone}</td>
    </tr>
    <tr>
      <td class="label">Date &amp; Time:</td>
      <td class="val" colspan="3">{submission_time}</td>
    </tr>
  </table>

  <div class="section-title">Story Script / Narrative:</div>
  <div class="script-box">
{news.description}
  </div>

  {byte_section}

  <div class="footer-note">
    Generated automatically by Prameya Digital News Desk Editorial Automation System | Confidential - Broadcast Production
  </div>
</body>
</html>"""


def generate_story_text_script(news, rep_name, rep_id, rep_phone):
    """
    Generates plain-text script for teleprompter and Notepad.
    """
    submission_time = news.created_at.strftime('%Y-%m-%d %H:%M:%S') if news.created_at else 'N/A'
    return f"""======================================================================
PRAMEYA DIGITAL NEWS NETWORK - FIELD STORY SCRIPT & DETAILS
======================================================================
STORY ID:           NL-STORY-{news.pk:05d}
HEADLINE:           {news.headline}
NEWS TYPE:          {news.news_type}
CATEGORY:           {news.category}
LOCATION:           {news.location}
DISTRICT:           {news.district}
REPORTER NAME:      {rep_name}
REPORTER ID:        {rep_id}
REPORTER PHONE:     {rep_phone}
SUBMISSION TIME:    {submission_time}
DESK STATUS:        {news.status} (SELECTED & APPROVED FOR BROADCAST)

----------------------------------------------------------------------
STORY SCRIPT / SCRIPT NARRATIVE:
----------------------------------------------------------------------
{news.description}

----------------------------------------------------------------------
BYTE / INTERVIEW DETAILS & SOUNDBITES:
----------------------------------------------------------------------
{news.byte_interview if news.byte_interview else 'No interview byte transcription recorded.'}

======================================================================
Generated by Prameya Digital News Desk Editorial Automation System
======================================================================
"""


def copy_approved_media_to_local_archive(news):
    """
    Saves a complete copy of the approved news story (Word Document + Script + Video + Audio + Package ZIP)
    directly to local storage folder on the server machine (MEDIA_ROOT/approved_local_storage/).
    This guarantees files exist safely in local office storage offline.
    """
    try:
        local_archive_dir = os.path.join(settings.MEDIA_ROOT, 'approved_local_storage')
        os.makedirs(local_archive_dir, exist_ok=True)
        clean_slug = slugify(news.headline, allow_unicode=True)[:35] or f"story_{news.pk}"
        clean_slug = re.sub(r'[\\/*?:"<>|]', "", clean_slug).strip() or f"story_{news.pk}"

        folder_name = f"NL_{news.pk:04d}_{clean_slug}"
        story_folder = os.path.join(local_archive_dir, folder_name)
        os.makedirs(story_folder, exist_ok=True)

        rep_name = news.reporter.name if news.reporter else (news.author.first_name or news.author.username)
        rep_id = news.reporter.reporter_id if (news.reporter and news.reporter.reporter_id) else "N/A"
        rep_phone = news.reporter.phone_number if news.reporter else "N/A"

        # 1. Save formatted Word Document (.doc)
        doc_content = generate_story_word_document(news, rep_name, rep_id, rep_phone)
        with open(os.path.join(story_folder, f"01_News_Document_{clean_slug}.doc"), 'w', encoding='utf-8') as f:
            f.write(doc_content)

        # 2. Save Text script (.txt)
        txt_content = generate_story_text_script(news, rep_name, rep_id, rep_phone)
        with open(os.path.join(story_folder, f"01_Story_Script_{clean_slug}.txt"), 'w', encoding='utf-8') as f:
            f.write(txt_content)

        # 3. Copy main media file (video/image)
        if news.media_file and hasattr(news.media_file, 'path') and os.path.exists(news.media_file.path):
            ext = os.path.splitext(news.media_file.path)[1]
            media_prefix = "02_Main_Video" if news.is_video else "02_Main_Image"
            dest_file = os.path.join(story_folder, f"{media_prefix}_{clean_slug}{ext}")
            shutil.copy2(news.media_file.path, dest_file)

        # 4. Copy byte media if exists
        if news.byte_media and hasattr(news.byte_media, 'path') and os.path.exists(news.byte_media.path):
            ext = os.path.splitext(news.byte_media.path)[1]
            dest_byte = os.path.join(story_folder, f"03_Byte_Interview_{clean_slug}{ext}")
            shutil.copy2(news.byte_media.path, dest_byte)

        # 5. Copy additional media if exists
        for idx, extra in enumerate(news.additional_media.all(), start=1):
            if extra.file and hasattr(extra.file, 'path') and os.path.exists(extra.file.path):
                ext = os.path.splitext(extra.file.path)[1]
                prefix = "04_Extra_Video" if extra.is_video else "04_Extra_Media"
                dest_extra = os.path.join(story_folder, f"{prefix}_{idx}_{clean_slug}{ext}")
                shutil.copy2(extra.file.path, dest_extra)

        # 6. Also save full standalone ZIP package in approved_local_storage
        zip_path = os.path.join(local_archive_dir, f"{folder_name}_Full_News_Package.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(story_folder):
                for f in files:
                    full_p = os.path.join(root, f)
                    arc_name = os.path.relpath(full_p, story_folder)
                    zip_file.write(full_p, arcname=f"{folder_name}/{arc_name}")
    except Exception:
        pass


def add_file_to_zip(zip_file, field_file, arcname):
    """
    Safely writes a Django FieldFile into a zipfile without loading whole file into RAM.
    Handles both local filesystem paths and remote storages (S3, Cloudinary, etc.).
    """
    if not field_file:
        return False
    # Method 1: If file exists on local disk, write directly
    try:
        if hasattr(field_file, 'path') and os.path.exists(field_file.path):
            zip_file.write(field_file.path, arcname=arcname)
            return True
    except Exception:
        pass

    # Method 2: Stream directly from storage into zip entry in 1MB chunks (0 RAM overhead)
    try:
        with field_file.open('rb') as src:
            with zip_file.open(arcname, 'w') as dest:
                shutil.copyfileobj(src, dest, length=1024 * 1024)
            return True
    except Exception:
        pass

    return False


@login_required
def news_download_single_media_view(request, pk):
    """
    Downloads COMPLETE news package (News Document .doc + Text Script .txt + Video + Audio + Extras)
    in a single structured ZIP archive.
    Uses disk-backed TemporaryFile and FileResponse streaming to prevent memory crashes and connection timeouts.
    """
    news = get_object_or_404(News, pk=pk)

    clean_slug = slugify(news.headline, allow_unicode=True)[:35] or f"story_{news.pk}"
    clean_slug = re.sub(r'[\\/*?:"<>|]', "", clean_slug).strip() or f"story_{news.pk}"

    rep_name = news.reporter.name if news.reporter else (news.author.first_name or news.author.username)
    rep_id = news.reporter.reporter_id if (news.reporter and news.reporter.reporter_id) else "N/A"
    rep_phone = news.reporter.phone_number if news.reporter else "N/A"

    folder_prefix = f"NL_{news.pk:04d}_{clean_slug}"
    filename = f"NL_{news.pk:04d}_{clean_slug}_Full_News_Package.zip"

    # 1. Fast path: check if pre-packaged archive exists in approved_local_storage
    today_str = (news.created_at or timezone.now()).strftime('%Y-%m-%d')
    local_archive_dir = os.path.join(settings.MEDIA_ROOT, 'approved_local_storage')
    pre_zip_path = os.path.join(local_archive_dir, f"{folder_prefix}_Full_News_Package.zip")
    if os.path.exists(pre_zip_path):
        try:
            return FileResponse(open(pre_zip_path, 'rb'), as_attachment=True, filename=filename, content_type='application/zip')
        except Exception:
            pass

    # 2. Dynamic generation: Use disk-backed TemporaryFile so RAM is never exhausted
    temp_zip = tempfile.TemporaryFile()

    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Full Word Document (.doc with formatting, header & table)
        doc_content = generate_story_word_document(news, rep_name, rep_id, rep_phone)
        zip_file.writestr(f"{folder_prefix}/01_News_Document_{clean_slug}.doc", doc_content.encode('utf-8'))

        # 2. Text Script file (.txt for teleprompter/Notepad)
        txt_content = generate_story_text_script(news, rep_name, rep_id, rep_phone)
        zip_file.writestr(f"{folder_prefix}/01_Story_Script_{clean_slug}.txt", txt_content.encode('utf-8'))

        # 3. Main Media File (Video / High-Res Image)
        if news.media_file:
            media_prefix = "02_Main_Video" if news.is_video else "02_Main_Image"
            ext = os.path.splitext(news.media_file.name)[1] or (".mp4" if news.is_video else ".jpg")
            arcname = f"{folder_prefix}/{media_prefix}_{clean_slug}{ext}"
            add_file_to_zip(zip_file, news.media_file, arcname)

        # 4. Byte Interview Media (Audio / Video)
        if news.byte_media:
            ext = os.path.splitext(news.byte_media.name)[1] or ".mp3"
            arcname = f"{folder_prefix}/03_Byte_Interview_{clean_slug}{ext}"
            add_file_to_zip(zip_file, news.byte_media, arcname)

        # 5. Additional Media Files
        for idx, extra in enumerate(news.additional_media.all(), start=1):
            if extra.file:
                prefix = "04_Extra_Video" if extra.is_video else "04_Extra_Media"
                ext = os.path.splitext(extra.file.name)[1] or (".mp4" if extra.is_video else ".jpg")
                arcname = f"{folder_prefix}/{prefix}_{idx}_{clean_slug}{ext}"
                add_file_to_zip(zip_file, extra.file, arcname)

    temp_zip.seek(0)
    response = FileResponse(temp_zip, as_attachment=True, filename=filename, content_type='application/zip')
    return response


@login_required
def input_update_news_status_view(request, pk):
    """
    Input Staff Action: Select (Approve & Forward to Desk) or Reject a news story.
    Supports both AJAX/Fetch and standard form POST.
    When Selected:
    - Status updated to Approved
    - Media copied to server's local storage folder (approved_local_storage)
    - Returns download_url so client browser immediately triggers complete news package ZIP download
    """
    if is_reporter_user(request.user):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        messages.error(request, "Permission denied.")
        return redirect('news_list')

    if request.method != 'POST':
        return redirect('input_news_verify_list')

    news = get_object_or_404(News, pk=pk)
    new_status = request.POST.get('status', '').strip()

    valid_statuses = dict(NEWS_STATUS_CHOICES)
    if new_status not in valid_statuses:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'success': False, 'error': 'Invalid status choice.'}, status=400)
        messages.error(request, "Invalid status choice.")
        return redirect('input_news_verify_list')

    if new_status == 'Rejected':
        # Media files deleted from storage/database on rejection, text preserved
        if news.media_file:
            try:
                news.media_file.delete(save=False)
            except Exception:
                pass
            news.media_file = None

        if news.byte_media:
            try:
                news.byte_media.delete(save=False)
            except Exception:
                pass
            news.byte_media = None

        for extra in news.additional_media.all():
            try:
                extra.file.delete(save=False)
            except Exception:
                pass
            extra.delete()

    news.status = new_status
    news.save()

    # If approved, save a local copy to server's local storage archive
    if news.status == 'Approved':
        copy_approved_media_to_local_archive(news)

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.POST.get('ajax') == '1' or
        'application/json' in request.headers.get('Accept', '')
    )

    if is_ajax:
        target_date = news.created_at.date()
        date_approved_count = News.objects.filter(created_at__date=target_date, status='Approved').count()
        date_rejected_count = News.objects.filter(created_at__date=target_date, status='Rejected').count()
        date_pending_count = News.objects.filter(created_at__date=target_date, status='Submitted').count()

        msg = f'Story "{news.headline}" approved and forwarded to Editorial Desk!' if news.status == 'Approved' else f'Story "{news.headline}" rejected.'

        clean_slug = slugify(news.headline, allow_unicode=True)[:35] or f"story_{news.pk}"
        clean_slug = re.sub(r'[\\/*?:"<>|]', "", clean_slug).strip() or f"story_{news.pk}"
        download_url = reverse('news_download_media', args=[news.pk])
        download_filename = f"NL_{news.pk:04d}_{clean_slug}_Full_News_Package.zip"

        return JsonResponse({
            'success': True,
            'pk': news.pk,
            'status': news.status,
            'status_label': 'Selected' if news.status == 'Approved' else news.status,
            'headline': news.headline,
            'date_approved_count': date_approved_count,
            'date_rejected_count': date_rejected_count,
            'date_pending_count': date_pending_count,
            'download_url': download_url if news.status == 'Approved' else None,
            'download_filename': download_filename,
            'has_media': bool(news.media_file or news.byte_media or news.additional_media.exists()),
            'message': msg
        })

    success_msg = f'News "{news.headline}" updated to "{news.status}".'
    if news.status == 'Approved':
        success_msg += ' Story has been forwarded to Editorial Desk and saved locally.'
    messages.success(request, success_msg)
    next_url = request.POST.get('next_url')
    if next_url:
        return redirect(next_url)
    return redirect('input_news_verify_list')


@login_required
def input_download_approved_news_zip_view(request):
    """
    Downloads approved news zip packages for Input Desk.
    """
    return desk_download_approved_news_zip_view(request)




# ==========================================
# Voice Over Portal Views (Voice Over Staff Access)
# ==========================================
@voice_over_required
def voice_over_dashboard_view(request):
    """
    Voice Over Staff Personal Dashboard.
    """
    voice_over_user = request.user.voice_over_profile
    total_approved = News.objects.filter(status='Approved').count()
    total_news = News.objects.count()
    avo_news_count = News.objects.filter(news_type__in=['AVO', 'AVO Byte']).count()
    all_tasks = News.objects.select_related('reporter', 'author', 'assigned_visual_editor').filter(
        assigned_voice_over=voice_over_user
    ).order_by('-assigned_at', '-created_at')
    
    pending_tasks = all_tasks.filter(Q(byte_media='') | Q(byte_media__isnull=True))
    completed_tasks = all_tasks.exclude(Q(byte_media='') | Q(byte_media__isnull=True))
    
    my_tasks_count = all_tasks.count()
    pending_count = pending_tasks.count()
    completed_count = completed_tasks.count()
    recent_news = News.objects.select_related('reporter', 'author').order_by('-created_at')[:8]

    context = {
        'active_page': 'voice_over_dashboard',
        'voice_over_user': voice_over_user,
        'total_approved': total_approved,
        'total_news': total_news,
        'avo_news_count': avo_news_count,
        'recent_news': recent_news,
        'my_tasks_count': my_tasks_count,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'recent_tasks': pending_tasks[:6],
    }
    return render(request, 'voice_over/dashboard.html', context)


@voice_over_required
def voice_over_my_task_view(request):
    """
    Voice Over Staff 'My Task' Portal:
    Displays pending stories assigned to this Voice Over artist waiting for voice recording.
    """
    _ensure_copy_editor_columns()
    vo = request.user.voice_over_profile
    all_tasks = News.objects.select_related(
        'reporter', 'author',
        'assigned_visual_editor', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer', 'assigned_voice_over'
    ).prefetch_related('additional_media').filter(
        assigned_voice_over=vo
    ).order_by('-assigned_at', '-created_at')

    # Pending tasks: where voice recording is not yet completed/sent
    pending_tasks = all_tasks.filter(Q(byte_media='') | Q(byte_media__isnull=True))
    completed_count = all_tasks.exclude(Q(byte_media='') | Q(byte_media__isnull=True)).count()

    query = request.GET.get('q', '').strip()
    if query:
        pending_tasks = pending_tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query)
        )

    context = {
        'active_page': 'voice_over_my_task',
        'voice_over_user': vo,
        'tasks': pending_tasks,
        'tasks_count': pending_tasks.count(),
        'pending_count': pending_tasks.count(),
        'completed_count': completed_count,
        'query': query,
    }
    return render(request, 'voice_over/my_task.html', context)


@voice_over_required
def voice_over_my_work_list_view(request):
    """
    Voice Over Staff 'My Work List' Portal:
    Displays stories where voice recording was completed, trimmed, and dispatched to Visual Editor.
    """
    _ensure_copy_editor_columns()
    vo = request.user.voice_over_profile
    all_tasks = News.objects.select_related(
        'reporter', 'author',
        'assigned_visual_editor', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer', 'assigned_voice_over'
    ).prefetch_related('additional_media').filter(
        assigned_voice_over=vo
    ).order_by('-assigned_at', '-created_at')

    # Completed tasks: where voice recording has been uploaded/sent
    completed_tasks = all_tasks.exclude(Q(byte_media='') | Q(byte_media__isnull=True))
    pending_count = all_tasks.filter(Q(byte_media='') | Q(byte_media__isnull=True)).count()

    query = request.GET.get('q', '').strip()
    if query:
        completed_tasks = completed_tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query)
        )

    context = {
        'active_page': 'voice_over_my_work_list',
        'voice_over_user': vo,
        'tasks': completed_tasks,
        'tasks_count': completed_tasks.count(),
        'completed_count': completed_tasks.count(),
        'pending_count': pending_count,
        'query': query,
    }
    return render(request, 'voice_over/my_work_list.html', context)


@voice_over_required
def voice_over_submit_audio_view(request, pk):
    """
    AJAX handler to receive recorded & trimmed voiceover audio from Voice Over artist.
    Saves audio to News.byte_media so it is immediately accessible to Visual Editor,
    then automatically moves story to Voice Over 'My Work List'.
    """
    news = get_object_or_404(News, pk=pk)
    vo = request.user.voice_over_profile

    if news.assigned_voice_over != vo and not is_admin_user(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if request.method == 'POST':
        audio_file = request.FILES.get('audio_file')
        if not audio_file:
            return JsonResponse({'success': False, 'error': 'No audio file provided.'}, status=400)

        # Generate unique voiceover filename
        timestamp = int(timezone.now().timestamp())
        ext = os.path.splitext(audio_file.name)[1].lower() if audio_file.name else '.wav'
        if not ext or ext not in ['.wav', '.mp3', '.webm', '.ogg', '.m4a']:
            ext = '.wav'
        filename = f"voiceover_{news.pk}_{timestamp}{ext}"

        news.byte_media.save(filename, audio_file, save=False)

        byte_interview = request.POST.get('byte_interview', '').strip()
        if byte_interview:
            news.byte_interview = byte_interview

        news.save()

        ve_name = news.assigned_visual_editor.name if news.assigned_visual_editor else "Visual Editor Desk"
        success_msg = f'Voiceover for "{news.headline}" has been saved and sent to Visual Editor ({ve_name})!'

        return JsonResponse({
            'success': True,
            'message': success_msg,
            'audio_url': news.byte_media.url if news.byte_media else '',
            'redirect_url': '/voice-over/my-work-list/'
        })

    return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)


@voice_over_required
def voice_over_profile_view(request):
    """
    Voice Over Staff Profile View.
    """
    voice_over_user = request.user.voice_over_profile
    context = {
        'active_page': 'voice_over_profile',
        'voice_over_user': voice_over_user,
    }
    return render(request, 'voice_over/profile.html', context)


# ==========================================
# Voice Over <-> Desk Chat Views
# ==========================================
@voice_over_required
def voice_over_chat_desk_view(request, desk_id=None):
    """
    Chat portal for Voice Over staff to communicate directly with Desk staff.
    Lists all Desk staff, shows unread messages from Desk, and opens conversation thread.
    """
    _ensure_voice_over_chat_table()
    vo = getattr(request.user, 'voice_over_profile', None)
    if not vo:
        messages.error(request, "No Voice Over profile found.")
        return redirect('voice_over_dashboard')

    desks = list(Desk.objects.filter(is_active=True).order_by('name'))

    for d in desks:
        d_status = d.get_last_seen_info()
        d.is_online = d_status['is_online']
        d.last_seen_text = d_status['text']
        d.unread_count = DeskVoiceOverChatMessage.objects.filter(
            desk=d,
            voice_over=vo,
            sender_type='desk',
            is_read=False
        ).count()
        latest_msg = DeskVoiceOverChatMessage.objects.filter(
            desk=d,
            voice_over=vo
        ).order_by('-created_at').first()
        d.latest_message = latest_msg

    active_desk = None
    if desk_id:
        active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    elif desks:
        # Default to Desk with unread or most recent message
        desks_with_msg = [d for d in desks if d.latest_message]
        if desks_with_msg:
            desks_with_msg.sort(key=lambda d: (d.unread_count > 0, d.latest_message.created_at), reverse=True)
            active_desk = desks_with_msg[0]
        else:
            active_desk = desks[0]

    chat_messages = []
    if active_desk:
        desk_status = active_desk.get_last_seen_info()
        active_desk.is_online = desk_status['is_online']
        active_desk.last_seen_text = desk_status['text']

        # Mark unread messages from this Desk as read
        DeskVoiceOverChatMessage.objects.filter(
            desk=active_desk,
            voice_over=vo,
            sender_type='desk',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskVoiceOverChatMessage.objects.filter(
            desk=active_desk,
            voice_over=vo
        ).order_by('created_at')

    context = {
        'active_page': 'voice_over_chat_desk',
        'voice_over_user': vo,
        'desks': desks,
        'active_desk': active_desk,
        'chat_messages': chat_messages,
    }
    return render(request, 'voice_over/chat_desk.html', context)


@voice_over_required
def voice_over_send_chat_message_view(request, desk_id):
    """
    POST/AJAX endpoint for Voice Over staff to send a message to Desk.
    """
    _ensure_voice_over_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    vo = getattr(request.user, 'voice_over_profile', None)
    if not vo:
        return JsonResponse({'success': False, 'error': 'Voice Over profile not found.'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskVoiceOverChatMessage.objects.create(
        desk=active_desk,
        voice_over=vo,
        sender_type='voice_over',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    VoiceOverUser.objects.filter(pk=vo.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': vo.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('voice_over_chat_desk_with_desk', desk_id=active_desk.pk)


@voice_over_required
def voice_over_get_chat_messages_api(request, desk_id):
    """
    GET AJAX polling endpoint for Voice Over staff.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Desk as read.
    """
    _ensure_voice_over_chat_table()
    vo = getattr(request.user, 'voice_over_profile', None)
    if not vo:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskVoiceOverChatMessage.objects.filter(
        desk=active_desk,
        voice_over=vo,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='desk', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskVoiceOverChatMessage.objects.filter(
        voice_over=vo,
        sender_type='desk',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': active_desk.name if m.sender_type == 'desk' else vo.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': timezone.localtime(m.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(m.created_at).strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    VoiceOverUser.objects.filter(pk=vo.pk).update(last_seen=timezone.now())

    active_desk.refresh_from_db(fields=['last_seen'])
    desk_status = active_desk.get_last_seen_info()

    read_message_ids = list(DeskVoiceOverChatMessage.objects.filter(
        desk=active_desk,
        voice_over=vo,
        sender_type='voice_over',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': desk_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Copy Editor Portal Views (Copy Editor Staff Access)
# ==========================================
def _ensure_copy_editor_columns():
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(app_news);")
            cols = [r[1] for r in cursor.fetchall()]
            if cols:
                if 'edited_by_copy_editor_id' not in cols:
                    try:
                        cursor.execute("ALTER TABLE app_news ADD COLUMN edited_by_copy_editor_id integer NULL REFERENCES app_copyeditor(id);")
                    except Exception:
                        pass
                if 'script_edited_at' not in cols:
                    try:
                        cursor.execute("ALTER TABLE app_news ADD COLUMN script_edited_at datetime NULL;")
                    except Exception:
                        pass
    except Exception:
        pass


@copy_editor_required
def copy_editor_dashboard_view(request):
    """
    Copy Editor Staff Personal Dashboard.
    """
    _ensure_copy_editor_columns()
    copy_editor_user = request.user.copy_editor_profile
    total_approved = News.objects.filter(status='Approved').count()
    total_news = News.objects.count()
    pending_news = News.objects.filter(status='Submitted').count()
    my_tasks = News.objects.select_related('reporter', 'author', 'edited_by_copy_editor').filter(
        assigned_copy_editor=copy_editor_user
    ).order_by('-assigned_at', '-created_at')
    my_tasks_count = my_tasks.count()
    pending_count = my_tasks.filter(is_script_edited_by_copy_editor=False).count()
    completed_count = my_tasks.filter(is_script_edited_by_copy_editor=True).count()
    recent_news = News.objects.select_related('reporter', 'author').order_by('-created_at')[:8]

    context = {
        'active_page': 'copy_editor_dashboard',
        'copy_editor_user': copy_editor_user,
        'total_approved': total_approved,
        'total_news': total_news,
        'pending_news': pending_news,
        'recent_news': recent_news,
        'my_tasks_count': my_tasks_count,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'recent_tasks': my_tasks[:6],
    }
    return render(request, 'copy_editor/dashboard.html', context)


@copy_editor_required
def copy_editor_my_task_view(request):
    """
    Copy Editor Staff 'My Task' Portal:
    Displays pending stories assigned to this Copy Editor by Desk that need proofreading & script editing
    before being forwarded to Visual Editor.
    """
    _ensure_copy_editor_columns()
    ce = request.user.copy_editor_profile
    all_assigned = News.objects.select_related(
        'reporter', 'author',
        'assigned_visual_editor', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer', 'assigned_voice_over'
    ).prefetch_related('additional_media').filter(
        assigned_copy_editor=ce
    ).order_by('-assigned_at', '-created_at')

    # Pending tasks: where copy editor has NOT yet forwarded to Visual Editor
    pending_tasks = all_assigned.filter(is_script_edited_by_copy_editor=False)
    completed_count = all_assigned.filter(is_script_edited_by_copy_editor=True).count()
    pending_count = pending_tasks.count()

    query = request.GET.get('q', '').strip()
    if query:
        pending_tasks = pending_tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query)
        )

    visual_editors = VisualEditor.objects.filter(is_active=True).order_by('name')

    context = {
        'active_page': 'copy_editor_my_task',
        'copy_editor_user': ce,
        'tasks': pending_tasks,
        'tasks_count': pending_tasks.count(),
        'pending_count': pending_count,
        'completed_count': completed_count,
        'query': query,
        'visual_editors': visual_editors,
    }
    return render(request, 'copy_editor/my_task.html', context)


@copy_editor_required
def copy_editor_my_task_list_view(request):
    """
    Copy Editor Staff 'My Task List' / 'My Work List' Portal:
    Displays all stories that have been edited by this Copy Editor and forwarded to Visual Editor.
    """
    _ensure_copy_editor_columns()
    ce = request.user.copy_editor_profile
    all_assigned = News.objects.select_related(
        'reporter', 'author',
        'assigned_visual_editor', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer', 'assigned_voice_over'
    ).prefetch_related('additional_media').filter(
        assigned_copy_editor=ce
    ).order_by('-sent_to_visual_editor_at', '-assigned_at', '-created_at')

    # Completed/Forwarded tasks: where copy editor has forwarded to Visual Editor
    completed_tasks = all_assigned.filter(is_script_edited_by_copy_editor=True)
    pending_count = all_assigned.filter(is_script_edited_by_copy_editor=False).count()
    completed_count = completed_tasks.count()

    query = request.GET.get('q', '').strip()
    if query:
        completed_tasks = completed_tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query) |
            Q(assigned_visual_editor__name__icontains=query)
        )

    visual_editors = VisualEditor.objects.filter(is_active=True).order_by('name')

    context = {
        'active_page': 'copy_editor_my_task_list',
        'copy_editor_user': ce,
        'tasks': completed_tasks,
        'tasks_count': completed_tasks.count(),
        'completed_count': completed_count,
        'pending_count': pending_count,
        'query': query,
        'visual_editors': visual_editors,
    }
    return render(request, 'copy_editor/my_task_list.html', context)


@copy_editor_required
def copy_editor_edit_script_view(request, pk):
    """
    Copy Editor dedicated Script Editor & Dispatch View:
    Allows Copy Editor to ONLY edit the script narrative (and headline).
    Provides direct forwarding to the selected Visual Editor.
    """
    _ensure_copy_editor_columns()
    ce = request.user.copy_editor_profile
    news = get_object_or_404(News, pk=pk, assigned_copy_editor=ce)
    visual_editors = VisualEditor.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        headline = request.POST.get('headline', '').strip()
        description = request.POST.get('description', '').strip()
        visual_editor_id = request.POST.get('visual_editor_id', '').strip()
        ve_notes = request.POST.get('ve_notes', '').strip()
        action_type = request.POST.get('action_type', 'save').strip()

        # Update narrative script (and headline if given)
        if description:
            news.description = description
        if headline:
            news.headline = headline

        # Mark that copy editor has edited and saved the script
        news.is_script_edited_by_copy_editor = True
        news.edited_by_copy_editor = ce
        news.script_edited_at = timezone.now()
        if not news.assigned_copy_editor:
            news.assigned_copy_editor = ce

        assigned_ve_name = None
        # Forward to Visual Editor ONLY IF action_type == 'send_ve'
        if action_type == 'send_ve':
            news.sent_to_visual_editor_at = timezone.now()

            if visual_editor_id and visual_editor_id.isdigit():
                try:
                    ve = VisualEditor.objects.get(pk=int(visual_editor_id), is_active=True)
                    news.assigned_visual_editor = ve
                    news.assigned_at = timezone.now()
                    assigned_ve_name = ve.name
                except (VisualEditor.DoesNotExist, ValueError):
                    pass
            elif news.assigned_visual_editor:
                assigned_ve_name = news.assigned_visual_editor.name

            if ve_notes:
                note_text = f"[{ce.name} - Copy Editor]: {ve_notes}"
                if news.desk_notes:
                    news.desk_notes = f"{news.desk_notes}\n{note_text}"
                else:
                    news.desk_notes = note_text

        news.save()

        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
        if is_ajax:
            if action_type == 'send_ve':
                ve_display = assigned_ve_name or 'Visual Editor'
                msg = f'Script polished by {ce.name} and forwarded to {ve_display}! Moved to My Task List.'
            else:
                msg = f'Script saved by {ce.name} successfully!'
            return JsonResponse({
                'status': 'success',
                'message': msg,
                'news_id': news.pk,
                'headline': news.headline,
                'description': news.description,
                'editor_name': ce.name,
                'is_script_edited': True,
                'assigned_ve_name': assigned_ve_name,
                'assigned_ve_id': news.assigned_visual_editor.pk if news.assigned_visual_editor else None,
            })

        if action_type == 'send_ve':
            ve_display = assigned_ve_name or 'Visual Editor'
            messages.success(request, f'Script updated by {ce.name} and story forwarded to {ve_display}!')
            return redirect('copy_editor_my_task_list')
        else:
            messages.success(request, f'Story script saved by {ce.name} successfully!')
            return redirect('copy_editor_my_task')

    context = {
        'active_page': 'copy_editor_my_task',
        'copy_editor_user': ce,
        'news': news,
        'visual_editors': visual_editors,
    }
    return render(request, 'copy_editor/edit_script.html', context)


@copy_editor_required
def copy_editor_profile_view(request):
    """
    Copy Editor Staff Profile View.
    """
    copy_editor_user = request.user.copy_editor_profile
    pending_count = News.objects.filter(assigned_copy_editor=copy_editor_user, is_script_edited_by_copy_editor=False).count()
    completed_count = News.objects.filter(assigned_copy_editor=copy_editor_user, is_script_edited_by_copy_editor=True).count()
    context = {
        'active_page': 'copy_editor_profile',
        'copy_editor_user': copy_editor_user,
        'pending_count': pending_count,
        'completed_count': completed_count,
    }
    return render(request, 'copy_editor/profile.html', context)


# ==========================================
# Copy Editor <-> Desk Chat Views
# ==========================================
@copy_editor_required
def copy_editor_chat_desk_view(request, desk_id=None):
    """
    Chat portal for Copy Editor to communicate directly with Desk staff.
    Lists all Desk staff, shows unread messages from Desk, and opens conversation thread.
    """
    _ensure_copy_chat_table()
    ce = getattr(request.user, 'copy_editor_profile', None)
    if not ce:
        messages.error(request, "No Copy Editor profile found.")
        return redirect('copy_editor_dashboard')

    desks = list(Desk.objects.filter(is_active=True).order_by('name'))

    for d in desks:
        d_status = d.get_last_seen_info()
        d.is_online = d_status['is_online']
        d.last_seen_text = d_status['text']
        d.unread_count = DeskCopyChatMessage.objects.filter(
            desk=d,
            copy_editor=ce,
            sender_type='desk',
            is_read=False
        ).count()
        latest_msg = DeskCopyChatMessage.objects.filter(
            desk=d,
            copy_editor=ce
        ).order_by('-created_at').first()
        d.latest_message = latest_msg

    active_desk = None
    if desk_id:
        active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    elif desks:
        # Default to Desk with unread or most recent message
        desks_with_msg = [d for d in desks if d.latest_message]
        if desks_with_msg:
            desks_with_msg.sort(key=lambda d: (d.unread_count > 0, d.latest_message.created_at), reverse=True)
            active_desk = desks_with_msg[0]
        else:
            active_desk = desks[0]

    chat_messages = []
    if active_desk:
        desk_status = active_desk.get_last_seen_info()
        active_desk.is_online = desk_status['is_online']
        active_desk.last_seen_text = desk_status['text']

        # Mark unread messages from this Desk as read
        DeskCopyChatMessage.objects.filter(
            desk=active_desk,
            copy_editor=ce,
            sender_type='desk',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskCopyChatMessage.objects.filter(
            desk=active_desk,
            copy_editor=ce
        ).order_by('created_at')

    context = {
        'active_page': 'copy_editor_chat_desk',
        'copy_editor_user': ce,
        'desks': desks,
        'active_desk': active_desk,
        'chat_messages': chat_messages,
    }
    return render(request, 'copy_editor/chat_desk.html', context)


@copy_editor_required
def copy_editor_send_chat_message_view(request, desk_id):
    """
    POST/AJAX endpoint for Copy Editor to send a message to Desk.
    """
    _ensure_copy_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    ce = getattr(request.user, 'copy_editor_profile', None)
    if not ce:
        return JsonResponse({'success': False, 'error': 'Copy Editor profile not found.'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskCopyChatMessage.objects.create(
        desk=active_desk,
        copy_editor=ce,
        sender_type='copy_editor',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    CopyEditor.objects.filter(pk=ce.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': ce.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('copy_editor_chat_desk_with_desk', desk_id=active_desk.pk)


@copy_editor_required
def copy_editor_get_chat_messages_api(request, desk_id):
    """
    GET AJAX polling endpoint for Copy Editor.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Desk as read.
    """
    _ensure_copy_chat_table()
    ce = getattr(request.user, 'copy_editor_profile', None)
    if not ce:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskCopyChatMessage.objects.filter(
        desk=active_desk,
        copy_editor=ce,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='desk', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskCopyChatMessage.objects.filter(
        copy_editor=ce,
        sender_type='desk',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': active_desk.name if m.sender_type == 'desk' else ce.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': timezone.localtime(m.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(m.created_at).strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    CopyEditor.objects.filter(pk=ce.pk).update(last_seen=timezone.now())

    active_desk.refresh_from_db(fields=['last_seen'])
    desk_status = active_desk.get_last_seen_info()

    read_message_ids = list(DeskCopyChatMessage.objects.filter(
        desk=active_desk,
        copy_editor=ce,
        sender_type='copy_editor',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': desk_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# Visual Editor Portal Views (Visual Editor Staff Access)
# ==========================================
@visual_editor_required
def visual_editor_dashboard_view(request):
    """
    Visual Editor Staff Personal Dashboard.
    """
    _ensure_copy_editor_columns()
    visual_editor_user = request.user.visual_editor_profile
    total_approved = News.objects.filter(status='Approved').count()
    total_news = News.objects.count()
    pending_news = News.objects.filter(status='Submitted').count()
    my_tasks = News.objects.select_related(
        'reporter', 'author',
        'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer',
        'assigned_voice_over',
        'assigned_social_media'
    ).prefetch_related('additional_media').filter(
        assigned_visual_editor=visual_editor_user
    ).order_by('-assigned_at', '-created_at')
    my_tasks_count = my_tasks.count()
    recent_news = News.objects.select_related('reporter', 'author').order_by('-created_at')[:8]

    context = {
        'active_page': 'visual_editor_dashboard',
        'visual_editor_user': visual_editor_user,
        'total_approved': total_approved,
        'total_news': total_news,
        'pending_news': pending_news,
        'recent_news': recent_news,
        'my_tasks_count': my_tasks_count,
        'recent_tasks': my_tasks[:6],
    }
    return render(request, 'visual_editor/dashboard.html', context)


@visual_editor_required
def visual_editor_my_task_view(request):
    """
    Visual Editor Staff 'My Task' Portal:
    Displays all stories assigned to this Visual Editor by Desk.
    Provides direct action button to open Video Studio for trimming and graphics.
    """
    _ensure_copy_editor_columns()
    ve = request.user.visual_editor_profile
    tasks = News.objects.select_related(
        'reporter', 'author',
        'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_graphic_designer',
        'assigned_voice_over',
        'assigned_social_media'
    ).prefetch_related('additional_media').filter(
        assigned_visual_editor=ve
    ).order_by('-assigned_at', '-created_at')

    query = request.GET.get('q', '').strip()
    if query:
        tasks = tasks.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(district__icontains=query)
        )

    context = {
        'active_page': 'visual_editor_my_task',
        'visual_editor_user': ve,
        'tasks': tasks,
        'tasks_count': tasks.count(),
        'query': query,
    }
    return render(request, 'visual_editor/my_task.html', context)


@visual_editor_required
def visual_editor_profile_view(request):
    """
    Visual Editor Staff Profile View.
    """
    visual_editor_user = request.user.visual_editor_profile
    context = {
        'active_page': 'visual_editor_profile',
        'visual_editor_user': visual_editor_user,
    }
    return render(request, 'visual_editor/profile.html', context)


# ==========================================
# Visual Editor <-> Desk Chat Views
# ==========================================
@visual_editor_required
def visual_editor_chat_desk_view(request, desk_id=None):
    """
    Chat portal for Visual Editor to communicate directly with Desk staff.
    Lists all Desk staff, shows unread messages from Desk, and opens conversation thread.
    """
    _ensure_chat_table()
    ve = getattr(request.user, 'visual_editor_profile', None)
    if not ve:
        messages.error(request, "No Visual Editor profile found.")
        return redirect('visual_editor_dashboard')

    desks = list(Desk.objects.filter(is_active=True).order_by('name'))

    for d in desks:
        d_status = d.get_last_seen_info()
        d.is_online = d_status['is_online']
        d.last_seen_text = d_status['text']
        d.unread_count = DeskVisualChatMessage.objects.filter(
            desk=d,
            visual_editor=ve,
            sender_type='desk',
            is_read=False
        ).count()
        latest_msg = DeskVisualChatMessage.objects.filter(
            desk=d,
            visual_editor=ve
        ).order_by('-created_at').first()
        d.latest_message = latest_msg

    active_desk = None
    if desk_id:
        active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    elif desks:
        # Default to Desk with unread or most recent message
        desks_with_msg = [d for d in desks if d.latest_message]
        if desks_with_msg:
            desks_with_msg.sort(key=lambda d: (d.unread_count > 0, d.latest_message.created_at), reverse=True)
            active_desk = desks_with_msg[0]
        else:
            active_desk = desks[0]

    chat_messages = []
    if active_desk:
        desk_status = active_desk.get_last_seen_info()
        active_desk.is_online = desk_status['is_online']
        active_desk.last_seen_text = desk_status['text']

        # Mark unread messages from this Desk as read
        DeskVisualChatMessage.objects.filter(
            desk=active_desk,
            visual_editor=ve,
            sender_type='desk',
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        chat_messages = DeskVisualChatMessage.objects.filter(
            desk=active_desk,
            visual_editor=ve
        ).order_by('created_at')

    context = {
        'active_page': 'visual_editor_chat_desk',
        'visual_editor_user': ve,
        'desks': desks,
        'active_desk': active_desk,
        'chat_messages': chat_messages,
    }
    return render(request, 'visual_editor/chat_desk.html', context)


@visual_editor_required
def visual_editor_send_chat_message_view(request, desk_id):
    """
    POST/AJAX endpoint for Visual Editor to send a message to Desk.
    """
    _ensure_chat_table()
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    ve = getattr(request.user, 'visual_editor_profile', None)
    if not ve:
        return JsonResponse({'success': False, 'error': 'Visual Editor profile not found.'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    msg_text = request.POST.get('message', '').strip()
    attachment = request.FILES.get('attachment')

    if not msg_text and not attachment:
        return JsonResponse({'success': False, 'error': 'Please enter a message or select an attachment.'}, status=400)

    chat_msg = DeskVisualChatMessage.objects.create(
        desk=active_desk,
        visual_editor=ve,
        sender_type='visual_editor',
        sender_user=request.user,
        message=msg_text,
        attachment=attachment,
        is_read=False,
    )
    VisualEditor.objects.filter(pk=ve.pk).update(last_seen=timezone.now())

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == '1'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message_id': chat_msg.pk,
            'sender_type': chat_msg.sender_type,
            'sender_name': ve.name,
            'message': chat_msg.message,
            'attachment_url': chat_msg.attachment.url if chat_msg.attachment else None,
            'attachment_name': os.path.basename(chat_msg.attachment.name) if chat_msg.attachment else None,
            'is_read': chat_msg.is_read,
            'created_at_formatted': timezone.localtime(chat_msg.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(chat_msg.created_at).strftime('%d %b %Y'),
        })

    return redirect('visual_editor_chat_desk_with_desk', desk_id=active_desk.pk)


@visual_editor_required
def visual_editor_get_chat_messages_api(request, desk_id):
    """
    GET AJAX polling endpoint for Visual Editor.
    Returns new messages after `last_id`.
    Automatically marks incoming messages from Desk as read.
    """
    _ensure_chat_table()
    ve = getattr(request.user, 'visual_editor_profile', None)
    if not ve:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    active_desk = get_object_or_404(Desk, pk=desk_id, is_active=True)
    last_id = request.GET.get('last_id', '0')
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    qs = DeskVisualChatMessage.objects.filter(
        desk=active_desk,
        visual_editor=ve,
        pk__gt=last_id
    ).order_by('created_at')

    incoming = qs.filter(sender_type='desk', is_read=False)
    if incoming.exists():
        incoming.update(is_read=True, read_at=timezone.now())

    total_unread = DeskVisualChatMessage.objects.filter(
        visual_editor=ve,
        sender_type='desk',
        is_read=False
    ).count()

    messages_data = []
    for m in qs:
        messages_data.append({
            'id': m.pk,
            'sender_type': m.sender_type,
            'sender_name': active_desk.name if m.sender_type == 'desk' else ve.name,
            'message': m.message,
            'attachment_url': m.attachment.url if m.attachment else None,
            'attachment_name': os.path.basename(m.attachment.name) if m.attachment else None,
            'is_read': m.is_read,
            'created_at_formatted': timezone.localtime(m.created_at).strftime('%I:%M %p'),
            'date_formatted': timezone.localtime(m.created_at).strftime('%d %b %Y'),
        })

    # Update current user's last_seen
    VisualEditor.objects.filter(pk=ve.pk).update(last_seen=timezone.now())

    active_desk.refresh_from_db(fields=['last_seen'])
    desk_status = active_desk.get_last_seen_info()

    read_message_ids = list(DeskVisualChatMessage.objects.filter(
        desk=active_desk,
        visual_editor=ve,
        sender_type='visual_editor',
        is_read=True
    ).values_list('pk', flat=True))

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'total_unread': total_unread,
        'contact_status': desk_status,
        'read_message_ids': read_message_ids,
    })


# ==========================================
# 7. News Management Views (Reporter, Admin, Desk)
# ==========================================
@login_required
def news_list_view(request):
    """
    Lists all submitted news stories with search, filter, and management actions.
    Role-aware: Reporters see their news / district news, Admin & Desk see all.
    """
    query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()
    category_filter = request.GET.get('category', '').strip()
    district_filter = request.GET.get('district', '').strip()
    status_filter = request.GET.get('status', '').strip()
    scope = request.GET.get('scope', '').strip()

    news_qs = News.objects.select_related('reporter', 'author').all()

    if is_reporter_user(request.user):
        reporter_profile = getattr(request.user, 'reporter_profile', None)
        if reporter_profile:
            news_qs = news_qs.filter(Q(author=request.user) | Q(reporter=reporter_profile))
        else:
            news_qs = news_qs.filter(author=request.user)

    # Base counts for the current user's scope before filters
    total_count = news_qs.count()
    approved_count = news_qs.filter(status='Approved').count()
    pending_count = news_qs.filter(status='Submitted').count()
    rejected_count = news_qs.filter(status='Rejected').count()

    if query:
        news_qs = news_qs.filter(
            Q(headline__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(district__icontains=query) |
            Q(byte_interview__icontains=query) |
            Q(reporter__name__icontains=query) |
            Q(reporter__reporter_id__icontains=query)
        )

    if type_filter:
        news_qs = news_qs.filter(news_type=type_filter)

    if category_filter:
        news_qs = news_qs.filter(category=category_filter)

    if district_filter:
        news_qs = news_qs.filter(district__iexact=district_filter)

    if status_filter:
        news_qs = news_qs.filter(status=status_filter)

    if is_reporter_user(request.user):
        all_districts = news_qs.values_list('district', flat=True).distinct().order_by('district')
    else:
        all_districts = News.objects.values_list('district', flat=True).distinct().order_by('district')
        if not all_districts:
            all_districts = Reporter.objects.values_list('district', flat=True).distinct().order_by('district')

    context = {
        'active_page': 'news_list',
        'news_list': news_qs,
        'total_count': total_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'all_districts': all_districts,
        'news_types': [c[0] for c in NEWS_TYPE_CHOICES],
        'news_categories': [c[0] for c in NEWS_CATEGORY_CHOICES],
        'news_statuses': [c[0] for c in NEWS_STATUS_CHOICES],
        'query': query,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'district_filter': district_filter,
        'status_filter': status_filter,
        'scope': scope,
        'base_template': get_base_template(request.user),
        'is_reporter': is_reporter_user(request.user),
        'is_desk': is_desk_user(request.user),
        'is_admin': is_admin_user(request.user),
    }
    return render(request, 'news/news_list.html', context)


@login_required
def news_add_view(request):
    """
    Add / Submit News form.
    Fields: News Headline, News Type (AVO, Byte, AVO Byte, PKG),
    Category, Location, District, News Description,
    Media File (Video/Image), Byte Interview (Optional), Byte Media (Optional).
    """
    errors = {}
    default_district = ''
    if is_reporter_user(request.user):
        default_district = request.user.reporter_profile.district

    form_data = {
        'district': default_district,
        'category': 'General',
        'news_type': 'AVO',
    }

    if request.method == 'POST':
        headline = request.POST.get('headline', '').strip()
        news_type = request.POST.get('news_type', '').strip()
        category = request.POST.get('category', '').strip()
        location = request.POST.get('location', '').strip()
        district = request.POST.get('district', '').strip()
        description = request.POST.get('description', '').strip()
        byte_interview = request.POST.get('byte_interview', '').strip()

        media_file = request.FILES.get('media_file')
        byte_media = request.FILES.get('byte_media')
        additional_media = request.FILES.getlist('additional_media')

        form_data = {
            'headline': headline,
            'news_type': news_type,
            'category': category,
            'location': location,
            'district': district,
            'description': description,
            'byte_interview': byte_interview,
        }

        # Validation
        if not headline:
            errors['headline'] = "News Headline is required."
        if not news_type:
            errors['news_type'] = "Please select News Type (AVO, Byte, AVO Byte, PKG)."
        elif news_type not in [c[0] for c in NEWS_TYPE_CHOICES]:
            errors['news_type'] = "Invalid News Type selected."
        if not location:
            errors['location'] = "Location / Incident Spot is required."
        if not district:
            errors['district'] = "District Name is required."
        if not description:
            errors['description'] = "News Description / Story Script is required."

        if not errors:
            news = News(
                headline=headline,
                news_type=news_type,
                category=category or 'General',
                location=location,
                district=district,
                description=description,
                byte_interview=byte_interview,
                author=request.user,
                status='Submitted'
            )
            if is_reporter_user(request.user):
                news.reporter = request.user.reporter_profile

            extra_files_to_save = list(additional_media)
            if media_file:
                news.media_file = media_file
            elif extra_files_to_save:
                news.media_file = extra_files_to_save.pop(0)

            if byte_media:
                news.byte_media = byte_media

            news.save()

            # Save all additional media files
            for extra_f in extra_files_to_save:
                NewsMedia.objects.create(news=news, file=extra_f)

            messages.success(request, f'News "{news.headline}" has been submitted successfully!')
            return redirect('news_list')

    context = {
        'active_page': 'news_add',
        'errors': errors,
        'form_data': form_data,
        'news_types': NEWS_TYPE_CHOICES,
        'news_categories': NEWS_CATEGORY_CHOICES,
        'base_template': get_base_template(request.user),
        'is_reporter': is_reporter_user(request.user),
        'is_desk': is_desk_user(request.user),
        'is_admin': is_admin_user(request.user),
    }
    return render(request, 'news/news_add.html', context)


@login_required
def news_detail_view(request, pk):
    """
    Detailed View of a Single News Story.
    Displays Headline, Type, Category, Location, District, Media Player/Image,
    Description, Byte Interview details, and Reporter Info.
    """
    _ensure_copy_editor_columns()
    news = get_object_or_404(News.objects.select_related(
        'reporter', 'author', 'assigned_copy_editor', 'edited_by_copy_editor',
        'assigned_visual_editor', 'assigned_voice_over', 'assigned_graphic_designer'
    ), pk=pk)

    if is_reporter_user(request.user):
        reporter_profile = getattr(request.user, 'reporter_profile', None)
        if news.author != request.user and news.reporter != reporter_profile:
            messages.error(request, "You do not have permission to view this news story.")
            return redirect('news_list')
    context = {
        'active_page': 'news_list',
        'news': news,
        'base_template': get_base_template(request.user),
        'is_reporter': is_reporter_user(request.user),
        'is_desk': is_desk_user(request.user),
        'is_admin': is_admin_user(request.user),
        'is_social_media': is_social_media_user(request.user),
        'is_visual_editor': is_visual_editor_user(request.user),
        'is_copy_editor': is_copy_editor_user(request.user),
        'is_voice_over': is_voice_over_user(request.user),
        'is_graphic_designer': is_graphic_designer_user(request.user),
    }
    return render(request, 'news/news_view.html', context)


@login_required
def news_edit_view(request, pk):
    """
    Edit existing News Story.
    """
    news = get_object_or_404(News, pk=pk)
    errors = {}

    # Check permission
    if is_reporter_user(request.user) and news.author != request.user and news.reporter != request.user.reporter_profile:
        messages.error(request, "You do not have permission to edit this news story.")
        return redirect('news_list')

    if request.method == 'POST':
        headline = request.POST.get('headline', '').strip()
        news_type = request.POST.get('news_type', '').strip()
        category = request.POST.get('category', '').strip()
        location = request.POST.get('location', '').strip()
        district = request.POST.get('district', '').strip()
        description = request.POST.get('description', '').strip()
        byte_interview = request.POST.get('byte_interview', '').strip()
        status = request.POST.get('status', news.status).strip()

        media_file = request.FILES.get('media_file')
        byte_media = request.FILES.get('byte_media')
        remove_media = request.POST.get('remove_media') == '1'
        remove_byte_media = request.POST.get('remove_byte_media') == '1'
        additional_media = request.FILES.getlist('additional_media')
        delete_media_ids = request.POST.getlist('delete_media_ids')

        if not headline:
            errors['headline'] = "News Headline is required."
        if not news_type:
            errors['news_type'] = "Please select News Type."
        if not location:
            errors['location'] = "Location is required."
        if not district:
            errors['district'] = "District is required."
        if not description:
            errors['description'] = "News Description is required."

        if not errors:
            news.headline = headline
            news.news_type = news_type
            news.category = category or 'General'
            news.location = location
            news.district = district
            news.description = description
            news.byte_interview = byte_interview

            if not is_reporter_user(request.user) and status in [c[0] for c in NEWS_STATUS_CHOICES]:
                news.status = status

            if remove_media and news.media_file:
                news.media_file.delete(save=False)
                news.media_file = None
            elif media_file:
                news.media_file = media_file

            if remove_byte_media and news.byte_media:
                news.byte_media.delete(save=False)
                news.byte_media = None
            elif byte_media:
                news.byte_media = byte_media

            news.save()

            # Process removal of selected additional media
            if delete_media_ids:
                for item_to_del in NewsMedia.objects.filter(news=news, id__in=delete_media_ids):
                    try:
                        item_to_del.file.delete(save=False)
                    except Exception:
                        pass
                    item_to_del.delete()

            # Process newly added additional media files
            for extra_f in additional_media:
                NewsMedia.objects.create(news=news, file=extra_f)

            messages.success(request, f'News "{news.headline}" was updated successfully!')
            return redirect('news_list')

    context = {
        'active_page': 'news_list',
        'news': news,
        'errors': errors,
        'news_types': NEWS_TYPE_CHOICES,
        'news_categories': NEWS_CATEGORY_CHOICES,
        'news_statuses': NEWS_STATUS_CHOICES,
        'base_template': get_base_template(request.user),
        'is_reporter': is_reporter_user(request.user),
        'is_desk': is_desk_user(request.user),
        'is_admin': is_admin_user(request.user),
    }
    return render(request, 'news/news_edit.html', context)


@login_required
def news_delete_view(request, pk):
    """
    Delete News Story with confirmation.
    """
    news = get_object_or_404(News, pk=pk)

    if is_reporter_user(request.user) and news.author != request.user and news.reporter != request.user.reporter_profile:
        messages.error(request, "You do not have permission to delete this news story.")
        return redirect('news_list')

    headline = news.headline
    if news.media_file:
        news.media_file.delete(save=False)
    if news.byte_media:
        news.byte_media.delete(save=False)
    for extra in news.additional_media.all():
        try:
            extra.file.delete(save=False)
        except Exception:
            pass
    news.delete()

    messages.success(request, f'News "{headline}" was deleted successfully.')
    return redirect('news_list')


# ==========================================
# 8. Desk News Verification Redirect
# (News Verification is managed exclusively by the Input Desk)
# ==========================================
@login_required
def desk_news_verify_list_view(request):
    """
    Redirect handler: News verification is managed exclusively by the Input Desk.
    Desk staff is redirected to desk_dashboard.
    Input staff is redirected to input_news_verify_list.
    """
    if is_input_user(request.user):
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            return redirect(f"/input/news/verify/?{query_string}")
        return redirect('input_news_verify_list')

    if is_desk_user(request.user) and not is_admin_user(request.user):
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            return redirect(f"/desk/my-word/?{query_string}")
        return redirect('desk_my_word')

    if is_admin_user(request.user):
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            return redirect(f"/input/news/verify/?{query_string}")
        return redirect('input_news_verify_list')

    return redirect('dashboard')


@login_required
def desk_update_news_status_view(request, pk):
    """
    Desk Staff Action: Select (Approve) or Reject a news story.
    Supports both AJAX/Fetch and standard form POST.
    """
    if is_reporter_user(request.user):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        messages.error(request, "Permission denied.")
        return redirect('news_list')

    if request.method != 'POST':
        return redirect('desk_news_verify_list')

    news = get_object_or_404(News, pk=pk)
    new_status = request.POST.get('status', '').strip()

    valid_statuses = dict(NEWS_STATUS_CHOICES)
    if new_status not in valid_statuses:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
            return JsonResponse({'success': False, 'error': 'Invalid status choice.'}, status=400)
        messages.error(request, "Invalid status choice.")
        return redirect('desk_news_verify_list')

    if new_status == 'Rejected':
        # Requirement: "reject ho jayega to wo text sab rahega media file data base se delete hoga"
        if news.media_file:
            try:
                news.media_file.delete(save=False)
            except Exception:
                pass
            news.media_file = None

        if news.byte_media:
            try:
                news.byte_media.delete(save=False)
            except Exception:
                pass
            news.byte_media = None

        for extra in news.additional_media.all():
            try:
                extra.file.delete(save=False)
            except Exception:
                pass
            extra.delete()

    news.status = new_status
    news.save()

    # If approved, save a local copy to server's local storage archive
    if news.status == 'Approved':
        copy_approved_media_to_local_archive(news)

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.POST.get('ajax') == '1' or
        'application/json' in request.headers.get('Accept', '')
    )

    if is_ajax:
        target_date = news.created_at.date()
        date_approved_count = News.objects.filter(created_at__date=target_date, status='Approved').count()
        date_rejected_count = News.objects.filter(created_at__date=target_date, status='Rejected').count()
        date_pending_count = News.objects.filter(created_at__date=target_date, status='Submitted').count()

        clean_slug = slugify(news.headline, allow_unicode=True)[:35] or f"story_{news.pk}"
        clean_slug = re.sub(r'[\\/*?:"<>|]', "", clean_slug).strip() or f"story_{news.pk}"
        download_url = reverse('news_download_media', args=[news.pk])
        download_filename = f"NL_{news.pk:04d}_{clean_slug}_Full_News_Package.zip"

        return JsonResponse({
            'success': True,
            'pk': news.pk,
            'status': news.status,
            'status_label': 'Selected' if news.status == 'Approved' else news.status,
            'headline': news.headline,
            'date_approved_count': date_approved_count,
            'date_rejected_count': date_rejected_count,
            'date_pending_count': date_pending_count,
            'download_url': download_url if news.status == 'Approved' else None,
            'download_filename': download_filename,
            'has_media': bool(news.media_file or news.byte_media or news.additional_media.exists()),
            'message': f'Story "{news.headline}" updated to {news.status}.'
        })

    messages.success(request, f'News "{news.headline}" has been updated to "{news.status}".')
    next_url = request.POST.get('next_url')
    if next_url:
        return redirect(next_url)
    if is_input_user(request.user):
        return redirect('input_news_verify_list')
    return redirect('desk_news_verify_list')


@login_required
def desk_download_approved_news_zip_view(request):
    """
    Downloads all Approved/Selected news stories and videos for the given date (or all)
    as a structured ZIP package for broadcast editing.
    """
    if is_reporter_user(request.user):
        messages.error(request, "Permission denied.")
        return redirect('news_list')

    date_str = request.GET.get('date', '').strip()
    news_qs = News.objects.select_related('reporter', 'author').filter(status='Approved')

    date_label = "All_Dates"
    if date_str and date_str != 'all':
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            news_qs = news_qs.filter(created_at__date=filter_date)
            date_label = date_str
        except ValueError:
            pass

    approved_list = list(news_qs.order_by('created_at'))

    if not approved_list:
        messages.warning(request, f"No approved / selected news stories found for date {date_str or 'selected criteria'} to download.")
        next_url = request.META.get('HTTP_REFERER') or 'desk_my_word'
        return redirect(next_url)

    temp_zip = tempfile.TemporaryFile()

    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        summary_lines = [
            "=" * 72,
            "PRAMEYA DIGITAL NEWS NETWORK - APPROVED BROADCAST PACKAGE",
            f"Package Date:      {date_label}",
            f"Total Stories:     {len(approved_list)}",
            f"Generated At:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Downloaded By:     {request.user.first_name or request.user.username} (Desk Editorial)",
            "=" * 72,
            "",
            "STORIES INCLUDED IN THIS ARCHIVE:",
            "-" * 72,
        ]

        for idx, item in enumerate(approved_list, 1):
            rep_name = item.reporter.name if item.reporter else (item.author.first_name or item.author.username)
            rep_id = item.reporter.reporter_id if (item.reporter and item.reporter.reporter_id) else "N/A"
            rep_phone = item.reporter.phone_number if item.reporter else "N/A"

            clean_slug = slugify(item.headline)[:35] or f"story_{item.pk}"
            folder_name = f"{idx:02d}_{item.news_type}_{clean_slug}"

            summary_lines.append(f"[{idx:02d}] {item.headline}")
            summary_lines.append(f"     Format: {item.news_type} | Category: {item.category} | District: {item.district}")
            summary_lines.append(f"     Reporter: {rep_name} ({rep_id} - {rep_phone}) | Time: {item.created_at.strftime('%H:%M')}")
            summary_lines.append(f"     Subfolder: {folder_name}/")
            summary_lines.append("")

            # 1. Story Details Text File
            story_txt = f"""======================================================================
PRAMEYA DIGITAL NEWS NETWORK - FIELD STORY SCRIPT & DETAILS
======================================================================
STORY ID:           NL-STORY-{item.pk:05d}
HEADLINE:           {item.headline}
NEWS TYPE:          {item.news_type}
CATEGORY:           {item.category}
LOCATION:           {item.location}
DISTRICT:           {item.district}
REPORTER NAME:      {rep_name}
REPORTER ID:        {rep_id}
REPORTER PHONE:     {rep_phone}
SUBMISSION TIME:    {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}
DESK STATUS:        APPROVED & SELECTED FOR BROADCAST

----------------------------------------------------------------------
STORY SCRIPT / SCRIPT NARRATIVE:
----------------------------------------------------------------------
{item.description}

----------------------------------------------------------------------
BYTE / INTERVIEW DETAILS & SOUNDBITES:
----------------------------------------------------------------------
{item.byte_interview if item.byte_interview else 'No interview byte transcription recorded.'}

======================================================================
Generated by Prameya Digital News Desk Editorial Automation System
======================================================================
"""
            zip_file.writestr(f"{folder_name}/Story_Details_{item.pk}.txt", story_txt.encode('utf-8'))

            # 2. Main Media File (Video / High-Res Image)
            if item.media_file:
                ext = os.path.splitext(item.media_file.name)[1] or (".mp4" if item.is_video else ".jpg")
                media_filename = f"{folder_name}/video_{clean_slug}{ext}" if item.is_video else f"{folder_name}/media_{clean_slug}{ext}"
                add_file_to_zip(zip_file, item.media_file, media_filename)

            # 2b. Additional Media Files
            for a_idx, extra in enumerate(item.additional_media.all(), start=2):
                if extra.file:
                    ext = os.path.splitext(extra.file.name)[1] or (".mp4" if extra.is_video else ".jpg")
                    prefix = "video" if extra.is_video else "media"
                    media_filename = f"{folder_name}/{prefix}_{clean_slug}_part{a_idx}{ext}"
                    add_file_to_zip(zip_file, extra.file, media_filename)

            # 3. Byte Interview Media (Audio / Video)
            if item.byte_media:
                ext = os.path.splitext(item.byte_media.name)[1] or ".mp3"
                arcname = f"{folder_name}/byte_media_{item.pk}{ext}"
                add_file_to_zip(zip_file, item.byte_media, arcname)

        summary_lines.append("=" * 72)
        summary_lines.append("END OF PACKAGE SUMMARY")
        summary_lines.append("=" * 72)
        zip_file.writestr("00_PACKAGE_SUMMARY.txt", "\n".join(summary_lines).encode('utf-8'))

    temp_zip.seek(0)
    filename = f"Prameya_Digital_Approved_News_{date_label}.zip"

    response = FileResponse(temp_zip, as_attachment=True, filename=filename, content_type='application/zip')
    return response


# ==========================================
# 10. AI News Script Assistant Endpoint
# ==========================================
@login_required
def ai_check_script_view(request):
    """
    AJAX endpoint: Checks and improves news script using AI.
    Corrects spelling, grammar, and formats as TV broadcast script.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST request required.'}, status=405)

    import json
    from . import ai_service

    try:
        if request.content_type == 'application/json' and request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        raw_text = data.get('text', '').strip()
        headline = data.get('headline', '').strip()
        news_type = data.get('news_type', 'AVO').strip()
        tone = data.get('tone', 'standard').strip()
        client_key = data.get('api_key', '').strip()

        if not raw_text:
            return JsonResponse({
                'success': False,
                'error': 'Please enter some news script or description to check.'
            }, status=400)

        result = ai_service.improve_news_script(
            raw_text=raw_text,
            headline=headline,
            news_type=news_type,
            tone=tone,
            client_key=client_key
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'AI Assistant Error: {str(e)}'
        }, status=500)


# ==========================================
# Media Download Approval Guard Views
# ==========================================
import random
import urllib.parse
from datetime import timedelta
from django.conf import settings


def validate_media_file_url(file_url, request=None):
    """
    Validates that file_url belongs to legitimate media paths or internal download routes of Prameya Digital.
    Blocks arbitrary external URLs (e.g. evil.com), dangerous protocols (javascript:, file:, data:),
    and path traversal attempts (../).
    Returns (is_valid: bool, cleaned_url: str, error_msg: str)
    """
    if not file_url or not isinstance(file_url, str):
        return False, '', 'Missing or empty file URL.'

    url_str = file_url.strip()

    # Block dangerous protocols
    lower_url = url_str.lower()
    for proto in ('javascript:', 'file:', 'data:', 'vbscript:', 'blob:', 'about:'):
        if lower_url.startswith(proto):
            return False, '', f'Forbidden URL protocol: {proto}'

    # Block directory traversal sequences
    if '..' in url_str or '%2e%2e' in lower_url or '\\' in url_str or '\0' in url_str:
        return False, '', 'Path traversal sequences are strictly forbidden.'

    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url_str)
    except Exception:
        return False, '', 'Malformed URL format.'

    # If absolute URL (scheme + netloc)
    if parsed.scheme in ('http', 'https'):
        # Verify host belongs to this application
        req_host = None
        if request:
            try:
                req_host = request.get_host().split(':')[0].lower()
            except Exception:
                pass

        allowed_hosts = set()
        if req_host:
            allowed_hosts.add(req_host)
        allowed_hosts.update(['127.0.0.1', 'localhost'])
        for h in getattr(settings, 'ALLOWED_HOSTS', []):
            allowed_hosts.add(h.split(':')[0].lower().lstrip('.'))

        parsed_host = (parsed.hostname or '').lower()
        if parsed_host not in allowed_hosts and '*' not in getattr(settings, 'ALLOWED_HOSTS', []):
            return False, '', 'External download URLs are not permitted. Only Prameya Digital media is authorized.'

        path = parsed.path
    else:
        path = parsed.path

    # Ensure path starts with recognized media or download prefixes
    # Prameya Digital media files live under /media/, /input/news/, or /desk/news/
    media_prefix = getattr(settings, 'MEDIA_URL', '/media/')
    allowed_prefixes = (
        media_prefix,
        '/input/news/',
        '/desk/news/',
    )

    clean_path = '/' + path.lstrip('/')
    is_allowed = any(clean_path.startswith(prefix) for prefix in allowed_prefixes)

    if not is_allowed:
        return False, '', 'URL does not point to a valid internal media file or download route.'

    return True, url_str, ''


@login_required
def request_download_passcode_view(request):
    """
    API for staff (Desk, Visual Editor, etc.) to request a download passcode from Admin.
    Input staff and Admin are exempt.
    Validates file URL, prevents external arbitrary URLs, and keeps audit trails.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    import json
    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = request.POST

    raw_file_url = data.get('file_url', '').strip()
    file_name = data.get('file_name', '').strip()

    # Validate file_url security (Issue 9)
    is_valid, file_url, url_error = validate_media_file_url(raw_file_url, request)
    if not is_valid:
        return JsonResponse({'success': False, 'error': url_error or 'Invalid file_url.'}, status=400)

    if not file_name:
        file_name = os.path.basename(file_url.split('?')[0]) or 'Media File'
    file_name = file_name[:255].replace('\0', '').strip()

    # Check if exempt: Admin or Input staff
    user = request.user
    if is_admin_user(user) or is_input_user(user) or user.is_superuser:
        return JsonResponse({
            'success': True,
            'is_exempt': True,
            'download_url': file_url
        })

    # Determine staff name and role
    requester_name = user.get_full_name() or user.username
    role_name = 'Staff'
    if hasattr(user, 'desk_profile'):
        requester_name = user.desk_profile.name
        role_name = 'Desk Staff'
    elif hasattr(user, 'visual_editor_profile'):
        requester_name = user.visual_editor_profile.name
        role_name = 'Visual Editor'
    elif hasattr(user, 'copy_editor_profile'):
        requester_name = user.copy_editor_profile.name
        role_name = 'Copy Editor'
    elif hasattr(user, 'voice_over_profile'):
        requester_name = user.voice_over_profile.name
        role_name = 'Voice Over'
    elif hasattr(user, 'social_media_profile'):
        requester_name = user.social_media_profile.name
        role_name = 'Social Media'
    elif hasattr(user, 'graphic_designer_profile'):
        requester_name = user.graphic_designer_profile.name
        role_name = 'Graphic Designer'
    elif hasattr(user, 'reporter_profile'):
        requester_name = user.reporter_profile.name
        role_name = 'Field Reporter'

    now = timezone.now()
    # Check if there is already an active non-expired unused non-rejected request for this exact file and user
    existing = MediaDownloadRequest.objects.filter(
        user=user,
        file_url=file_url,
        is_used=False,
        is_rejected=False,
        expires_at__gt=now
    ).order_by('-created_at').first()

    if existing:
        return JsonResponse({
            'success': True,
            'is_exempt': False,
            'request_id': existing.pk,
            'file_name': existing.file_name,
            'expires_in': max(0, int((existing.expires_at - now).total_seconds())),
            'message': 'Passcode already sent to Chief Editor / Admin.'
        })

    # Expire any previous unapproved requests for this file and user instead of deleting (Issue 8)
    MediaDownloadRequest.objects.filter(
        user=user,
        file_url=file_url,
        is_used=False,
        is_approved=False,
        is_rejected=False,
        expires_at__gt=now
    ).update(expires_at=now)

    # Generate 6-digit random passcode
    passcode = f"{random.randint(100000, 999999)}"
    expires_at = now + timedelta(minutes=15)

    req = MediaDownloadRequest.objects.create(
        user=user,
        requester_name=requester_name,
        role_name=role_name,
        file_url=file_url,
        file_name=file_name,
        passcode=passcode,
        is_approved=False,
        is_used=False,
        is_rejected=False,
        expires_at=expires_at,
    )

    return JsonResponse({
        'success': True,
        'is_exempt': False,
        'request_id': req.pk,
        'file_name': req.file_name,
        'expires_in': 900,
        'message': 'Passcode requested successfully! Please obtain the 6-digit code from Chief Editor / Admin.'
    })


@login_required
def verify_download_passcode_view(request):
    """
    Verify entered 6-digit passcode.
    Strictly restricted to the authenticated user's own request:
    - User ownership verified (Issue 2).
    - No global passcode fallback across users (Issue 3 & 7).
    - Correct passcode required.
    - Single-use enforced (Issue 4).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    import json
    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = request.POST

    request_id = data.get('request_id')
    passcode = str(data.get('passcode', '')).strip()

    if not passcode or len(passcode) != 6 or not passcode.isdigit():
        return JsonResponse({'success': False, 'error': 'Please enter a valid 6-digit passcode.'}, status=400)

    now = timezone.now()
    download_req = None

    # 1. Query strictly for THIS user (Issue 2 & 7)
    if request_id:
        try:
            req_id_int = int(request_id)
            download_req = MediaDownloadRequest.objects.filter(pk=req_id_int, user=request.user).first()
        except (ValueError, TypeError):
            download_req = None

    # 2. If not found by request_id, find strictly for THIS user by passcode (Issue 3: NO global fallback!)
    if not download_req:
        download_req = MediaDownloadRequest.objects.filter(
            user=request.user,
            passcode=passcode,
            is_used=False,
            is_rejected=False,
            expires_at__gt=now
        ).order_by('-created_at').first()

    if not download_req:
        # Check user's own history to provide accurate feedback
        history = MediaDownloadRequest.objects.filter(user=request.user, passcode=passcode).order_by('-created_at').first()
        if history:
            if getattr(history, 'is_rejected', False):
                return JsonResponse({
                    'success': False, 
                    'error': f'This download request was rejected by Chief Editor / Admin. {history.rejection_reason or ""}'.strip()
                }, status=400)
            if history.is_used:
                return JsonResponse({'success': False, 'error': 'This passcode has already been used. Please request a new one.'}, status=400)
            if history.is_expired():
                return JsonResponse({'success': False, 'error': 'Passcode has expired. Please request a new one.'}, status=400)

        return JsonResponse({'success': False, 'error': 'Incorrect passcode! Please check the 6-digit code with Admin.'}, status=400)

    # 3. Security checks on download_req:
    # Ownership:
    if download_req.user_id != request.user.pk:
        return JsonResponse({'success': False, 'error': 'Access denied: this authorization belongs to another account.'}, status=403)

    # Passcode must match:
    if download_req.passcode != passcode:
        return JsonResponse({'success': False, 'error': 'Incorrect passcode! Please check the 6-digit code with Admin.'}, status=400)

    # Must not be rejected:
    if getattr(download_req, 'is_rejected', False):
        return JsonResponse({
            'success': False, 
            'error': f'This download request was rejected by Chief Editor / Admin. {download_req.rejection_reason or ""}'.strip()
        }, status=400)

    # Must not be expired:
    if download_req.is_expired():
        return JsonResponse({'success': False, 'error': 'Passcode has expired. Please request a new one.'}, status=400)

    # Must not be already used (Issue 4):
    if download_req.is_used:
        return JsonResponse({'success': False, 'error': 'This passcode has already been used. Please request a new one.'}, status=400)

    # 4. Mark approved and used
    download_req.is_approved = True
    download_req.is_used = True
    download_req.save(update_fields=['is_approved', 'is_used'])

    return JsonResponse({
        'success': True,
        'message': '✓ Passcode verified successfully! Download starting...',
        'download_url': download_req.file_url,
        'file_name': download_req.file_name
    })


@login_required
def check_download_status_view(request):
    """
    Polling API: Requester modal checks every 3s if Admin clicked 'Quick Approve'.
    Strictly checks:
    - User ownership: Only request.user can poll their own request_id (Issue 2).
    - Single-use: Never returns approved: True once is_used is True (Issue 4).
    - Status reporting: Notifies client if rejected or expired.
    """
    raw_request_id = request.GET.get('request_id')
    if not raw_request_id:
        return JsonResponse({'approved': False, 'error': 'Missing request_id'}, status=400)

    try:
        req_id_int = int(raw_request_id)
    except (ValueError, TypeError):
        return JsonResponse({'approved': False, 'error': 'Invalid request_id'}, status=400)

    try:
        # Strictly verify ownership (Issue 2)
        download_req = MediaDownloadRequest.objects.get(pk=req_id_int, user=request.user)
    except MediaDownloadRequest.DoesNotExist:
        return JsonResponse({'approved': False, 'error': 'Request not found or access denied.'}, status=404)

    # Check if rejected (Issue 8)
    if getattr(download_req, 'is_rejected', False):
        return JsonResponse({
            'approved': False,
            'is_rejected': True,
            'error': f'Download request was rejected by Chief Editor / Admin. {download_req.rejection_reason or ""}'.strip()
        })

    # Check if expired (Issue 5)
    if download_req.is_expired():
        return JsonResponse({'approved': False, 'is_expired': True, 'error': 'Passcode has expired.'})

    # Check if already used (Issue 4: NEVER return approved: True if already used!)
    if download_req.is_used:
        return JsonResponse({
            'approved': False,
            'is_used': True,
            'error': 'This download authorization has already been used.'
        })

    # If approved by Admin and NOT yet used: mark used and release download URL once
    if download_req.is_approved:
        download_req.is_used = True
        download_req.save(update_fields=['is_used'])
        return JsonResponse({
            'approved': True,
            'download_url': download_req.file_url,
            'file_name': download_req.file_name
        })

    return JsonResponse({'approved': False, 'is_pending': True})


@login_required
def admin_download_requests_api(request):
    """
    API for Admin to get pending download requests and to approve/reject them.
    Validates request_id, action, expiry, and preserves audit history upon rejection (Issues 5, 6, 8).
    """
    if not (request.user.is_superuser or request.user.is_staff or is_admin_user(request.user)):
        return JsonResponse({'success': False, 'error': 'Admin access required.'}, status=403)

    if request.method == 'GET':
        now = timezone.now()
        pending = MediaDownloadRequest.objects.filter(
            is_approved=False,
            is_used=False,
            is_rejected=False,
            expires_at__gt=now
        ).order_by('-created_at')[:20]

        items = []
        for p in pending:
            time_left = max(0, int((p.expires_at - now).total_seconds()))
            items.append({
                'id': p.pk,
                'requester_name': p.requester_name,
                'role_name': p.role_name,
                'file_name': p.file_name,
                'passcode': p.passcode,
                'created_at': p.created_at.strftime('%I:%M %p'),
                'expires_in_mins': f"{time_left // 60}m {time_left % 60}s",
            })
        return JsonResponse({'success': True, 'count': len(items), 'requests': items})

    elif request.method == 'POST':
        import json
        try:
            data = json.loads(request.body) if request.body else request.POST
        except Exception:
            data = request.POST

        action = str(data.get('action', '')).strip().lower()
        raw_req_id = data.get('request_id')

        # 1. Validate request_id (Issue 6)
        if not raw_req_id:
            return JsonResponse({'success': False, 'error': 'Missing request_id.'}, status=400)
        try:
            req_id = int(raw_req_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid request_id format. Must be an integer.'}, status=400)

        # 2. Validate action (Issue 6)
        if action not in ['approve', 'reject']:
            return JsonResponse({'success': False, 'error': f"Invalid action '{action}'. Allowed: 'approve', 'reject'."}, status=400)

        # 3. Retrieve request
        try:
            download_req = MediaDownloadRequest.objects.get(pk=req_id)
        except MediaDownloadRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Download request not found.'}, status=404)

        now = timezone.now()

        # 4. Check expiry and state before approving (Issue 5 & 6)
        if action == 'approve':
            if download_req.is_expired():
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot approve: this request expired at {download_req.expires_at.strftime("%I:%M %p")}. Staff must request a fresh passcode.'
                }, status=400)

            if download_req.is_used:
                return JsonResponse({'success': False, 'error': 'Cannot approve: this request has already been used.'}, status=400)

            if getattr(download_req, 'is_rejected', False):
                return JsonResponse({'success': False, 'error': 'Cannot approve: this request has already been rejected.'}, status=400)

            download_req.is_approved = True
            download_req.approved_by = request.user
            download_req.save(update_fields=['is_approved', 'approved_by'])
            return JsonResponse({
                'success': True,
                'message': f'Approved download for {download_req.requester_name} ({download_req.role_name})!'
            })

        elif action == 'reject':
            # Preserve audit history (Issue 8) - DO NOT delete!
            rejection_reason = str(data.get('reason', '')).strip()[:255] or 'Rejected by Admin'
            download_req.is_rejected = True
            download_req.is_approved = False
            download_req.rejected_by = request.user
            download_req.rejected_at = now
            download_req.rejection_reason = rejection_reason
            download_req.save(update_fields=['is_rejected', 'is_approved', 'rejected_by', 'rejected_at', 'rejection_reason'])
            return JsonResponse({
                'success': True,
                'message': f'Download request for {download_req.requester_name} has been rejected (logged in audit history).'
            })

        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)


@admin_required
def admin_download_approvals_view(request):
    """
    Dedicated Admin page to view and manage all Media Download Approval requests & logs.
    Includes full audit filtering for pending, approved, downloaded, expired, and rejected requests.
    """
    status_filter = request.GET.get('status', 'all').strip().lower()
    now = timezone.now()
    qs = MediaDownloadRequest.objects.select_related('user', 'approved_by', 'rejected_by').all()

    if status_filter == 'pending':
        qs = qs.filter(is_approved=False, is_used=False, is_rejected=False, expires_at__gt=now)
    elif status_filter == 'approved':
        qs = qs.filter(is_approved=True, is_used=False, is_rejected=False)
    elif status_filter == 'used':
        qs = qs.filter(is_used=True)
    elif status_filter == 'expired':
        qs = qs.filter(is_used=False, is_approved=False, is_rejected=False, expires_at__lte=now)
    elif status_filter == 'rejected':
        qs = qs.filter(is_rejected=True)

    pending_count = MediaDownloadRequest.objects.filter(is_approved=False, is_used=False, is_rejected=False, expires_at__gt=now).count()
    rejected_count = MediaDownloadRequest.objects.filter(is_rejected=True).count()
    total_count = MediaDownloadRequest.objects.count()

    context = {
        'active_page': 'download_approvals',
        'requests': qs.order_by('-created_at')[:100],
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
        'status_filter': status_filter,
    }
    return render(request, 'admin/download_approvals.html', context)


# ==========================================
# 9. Live Broadcast & Field Streaming Views
# ==========================================

@reporter_required
@ensure_csrf_cookie
def reporter_live_view(request):
    """
    Field Reporter Mobile Live Broadcast View.
    Allows field reporters to preview camera, setup live headline,
    request live broadcast authorization from Social Media Desk,
    and broadcast live with real-time TV graphics & teleprompter cues.
    """
    reporter = request.user.reporter_profile
    active_session = LiveBroadcastSession.objects.filter(
        reporter=reporter,
        status__in=['pending', 'approved', 'live']
    ).first()

    setting = LiveStreamSetting.objects.first()

    context = {
        'active_page': 'reporter_live',
        'reporter': reporter,
        'active_session': active_session,
        'setting': setting,
        'district': reporter.district,
    }
    return render(request, 'reporter/live_broadcast.html', context)


@login_required
@ensure_csrf_cookie
def social_media_live_control_view(request):
    """
    Social Media / Editorial Live Broadcast Control Room.
    Gatekeeps incoming reporter requests, verifies QA preview,
    routes streams to YouTube/Facebook, triggers Emergency Kill Switch,
    and sends live cues to on-air reporters.
    """
    if not is_live_control_authorized(request.user):
        return redirect('dashboard')

    setting, _ = LiveStreamSetting.objects.get_or_create(id=1)
    active_broadcast = LiveBroadcastSession.objects.filter(status='live').select_related('reporter').first()
    pending_sessions = LiveBroadcastSession.objects.filter(status__in=['pending', 'approved']).select_related('reporter').order_by('-created_at')[:10]
    recent_sessions = LiveBroadcastSession.objects.filter(status='ended').select_related('reporter').order_by('-ended_at')[:10]

    context = {
        'active_page': 'social_media_live_control',
        'setting': setting,
        'active_broadcast': active_broadcast,
        'pending_sessions': pending_sessions,
        'recent_sessions': recent_sessions,
    }
    return render(request, 'social_media/live_control_room.html', context)


@login_required
def social_media_live_settings_view(request):
    """
    Configure YouTube and Facebook Live Stream RTMP credentials.
    """
    if not is_live_control_authorized(request.user):
        return redirect('dashboard')

    setting, _ = LiveStreamSetting.objects.get_or_create(id=1)

    if request.method == 'POST':
        setting.youtube_rtmp_url = request.POST.get('youtube_rtmp_url', setting.youtube_rtmp_url).strip()
        setting.youtube_stream_key = request.POST.get('youtube_stream_key', '').strip()
        setting.facebook_rtmp_url = request.POST.get('facebook_rtmp_url', setting.facebook_rtmp_url).strip()
        setting.facebook_stream_key = request.POST.get('facebook_stream_key', '').strip()
        setting.is_auto_record = request.POST.get('is_auto_record') == 'on'
        setting.save()
        messages.success(request, "Live Stream Broadcast credentials updated successfully!")
        return redirect('social_media_live_control')

    context = {
        'active_page': 'social_media_live_settings',
        'setting': setting,
    }
    return render(request, 'social_media/live_settings.html', context)


# ==========================================
# Real-time Broadcast APIs
# ==========================================

@csrf_exempt
@reporter_required
def api_reporter_request_live(request):
    """
    Reporter initiates a Live Broadcast Request.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    reporter = request.user.reporter_profile
    headline = request.POST.get('headline', '').strip()
    district = request.POST.get('district', reporter.district).strip()

    if not headline:
        headline = f"Ground Zero Live Field Report from {district}"

    # Close any stale session
    LiveBroadcastSession.objects.filter(reporter=reporter, status__in=['pending', 'approved']).update(status='ended', ended_at=timezone.now())

    session = LiveBroadcastSession.objects.create(
        reporter=reporter,
        headline=headline,
        district=district,
        status='pending'
    )

    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'status': session.status,
        'headline': session.headline,
        'message': 'Live broadcast request submitted to Social Media Desk!'
    })


@login_required
def api_reporter_poll_status(request, session_id):
    """
    Reporter mobile interface polls for status changes, destinations, and live cues.
    """
    session = get_object_or_404(LiveBroadcastSession, pk=session_id)
    elapsed = 0
    if session.started_at:
        end_time = session.ended_at or timezone.now()
        elapsed = int((end_time - session.started_at).total_seconds())

    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'status': session.status,
        'destination': session.destination,
        'destination_display': session.get_destination_display(),
        'current_cue': session.current_cue or '',
        'elapsed_seconds': elapsed,
        'headline': session.headline,
    })


@login_required
def api_social_pending_requests(request):
    """
    Social Media Desk polls for pending/live broadcast sessions.
    """
    if not is_live_control_authorized(request.user):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    pending = LiveBroadcastSession.objects.filter(status='pending').select_related('reporter').order_by('-created_at')[:10]
    active = LiveBroadcastSession.objects.filter(status='live').select_related('reporter').first()

    data_pending = []
    for s in pending:
        data_pending.append({
            'session_id': s.pk,
            'reporter_name': s.reporter.name,
            'reporter_phone': s.reporter.phone_number,
            'reporter_id': s.reporter.reporter_id or '',
            'district': s.district,
            'headline': s.headline,
            'created_at': s.created_at.strftime('%H:%M:%S'),
        })

    active_data = None
    if active:
        elapsed = int((timezone.now() - active.started_at).total_seconds()) if active.started_at else 0
        from .streaming_relay import relay_manager
        active_data = {
            'session_id': active.pk,
            'reporter_name': active.reporter.name,
            'reporter_id': active.reporter.reporter_id or '',
            'district': active.district,
            'headline': active.headline,
            'destination': active.get_destination_display(),
            'current_cue': active.current_cue or '',
            'elapsed_seconds': elapsed,
            'relay': relay_manager.get_status(active.pk),
            'preview_frame': relay_manager.get_preview(active.pk) or '',
        }

    return JsonResponse({
        'success': True,
        'pending_count': len(data_pending),
        'pending': data_pending,
        'pending_requests': data_pending,
        'active_broadcast': active_data,
    })


@csrf_exempt
@login_required
def api_social_approve_live(request):
    """
    Social Media Desk approves request and pushes stream Live On-Air.
    """
    if not is_live_control_authorized(request.user):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        session_id = request.POST.get('session_id')
        destination = request.POST.get('destination', 'youtube')
        session = LiveBroadcastSession.objects.filter(pk=session_id).first()
        if not session:
            return JsonResponse({'success': False, 'error': f'Broadcast session #{session_id} not found.'}, status=404)

        session.status = 'live'
        session.destination = destination
        session.approved_by = request.user
        session.started_at = timezone.now()
        session.current_cue = "✔ You are LIVE on YouTube / Facebook! Stand by for audio."
        session.save()

        # Pre-initialize streaming relay for YouTube / Facebook
        relay_started = False
        relay_msg = ""
        try:
            from .streaming_relay import relay_manager
            relay_started, relay_msg = relay_manager.start_session(session.pk, destination)
        except Exception as relay_err:
            relay_msg = str(relay_err)

        return JsonResponse({
            'success': True,
            'session_id': session.pk,
            'status': session.status,
            'destination': session.destination,
            'relay_started': relay_started,
            'relay_message': relay_msg,
            'message': f"Broadcast is now LIVE on {session.get_destination_display()}!"
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def api_social_send_cue(request):
    """
    Social Media Desk sends a real-time teleprompter cue to the on-air reporter.
    """
    if not is_live_control_authorized(request.user):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    session_id = request.POST.get('session_id')
    cue_text = request.POST.get('cue_text', '').strip()
    session = get_object_or_404(LiveBroadcastSession, pk=session_id)

    session.current_cue = cue_text
    session.save(update_fields=['current_cue'])

    return JsonResponse({'success': True, 'cue': cue_text})


@csrf_exempt
@login_required
def api_social_stop_live(request):
    """
    End broadcast or trigger Emergency Kill Switch.
    """
    if not is_live_control_authorized(request.user):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    session_id = request.POST.get('session_id')
    reason = request.POST.get('reason', 'Normal end').strip()
    session = get_object_or_404(LiveBroadcastSession, pk=session_id)

    session.status = 'ended'
    session.ended_at = timezone.now()
    session.current_cue = f"Broadcast Ended ({reason})"
    session.save()

    # Terminate FFmpeg background relay
    from .streaming_relay import relay_manager
    relay_manager.stop_session(session_id)

    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'status': session.status,
        'message': f'Broadcast session ended successfully ({reason}).'
    })


@csrf_exempt
@login_required
def api_live_stream_chunk(request):
    """
    Receives real-time WebM video chunks from reporter's browser during a Live session,
    and pipes them to FFmpeg to push into the YouTube / Facebook RTMP stream.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    session_id = request.POST.get('session_id')
    chunk_file = request.FILES.get('video_chunk')
    chunk_index = request.POST.get('chunk_index', 0)

    if not session_id or not chunk_file:
        return JsonResponse({'success': False, 'error': 'session_id and video_chunk required'}, status=400)

    try:
        session = LiveBroadcastSession.objects.filter(pk=session_id).first()
        if not session:
            return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)

        if session.status != 'live':
            return JsonResponse({
                'success': False,
                'session_status': session.status,
                'error': f'Session status is {session.status}, not live'
            }, status=200)

        chunk_bytes = chunk_file.read()
        from .streaming_relay import relay_manager

        preview_frame = request.POST.get('preview_frame')
        if preview_frame:
            relay_manager.update_preview(session_id, preview_frame)

        success, msg = relay_manager.write_chunk(session_id, chunk_bytes, destination=session.destination)

        return JsonResponse({
            'success': success,
            'session_id': session_id,
            'chunk_index': chunk_index,
            'bytes_relayed': len(chunk_bytes),
            'message': msg
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def api_live_preview(request, session_id):
    """
    Returns the latest live video frame snapshot for Social Media Control Room monitor.
    """
    from .streaming_relay import relay_manager
    preview = relay_manager.get_preview(session_id)
    return JsonResponse({
        'success': bool(preview),
        'session_id': session_id,
        'preview_frame': preview or ''
    })


@login_required
def api_live_relay_status(request, session_id):
    """
    Returns real-time health and packet statistics of the FFmpeg RTMP relay.
    """
    from .streaming_relay import relay_manager
    status = relay_manager.get_status(session_id)
    return JsonResponse({
        'success': True,
        'session_id': session_id,
        'relay': status
    })


@csrf_exempt
@login_required
def api_live_save_recording(request):
    """
    Saves the recorded MP4/WebM video of the live broadcast session
    and automatically registers it in News Media so Editors can extract bytes!
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    session_id = request.POST.get('session_id')
    video_file = request.FILES.get('video_file')

    if not session_id or not video_file:
        return JsonResponse({'success': False, 'error': 'session_id and video_file required'}, status=400)

    # Ensure relay is stopped
    from .streaming_relay import relay_manager
    relay_manager.stop_session(session_id)

    session = get_object_or_404(LiveBroadcastSession, pk=session_id)
    session.recorded_file = video_file
    session.save(update_fields=['recorded_file'])

    # Auto-create News entry if setting is auto_record
    setting = LiveStreamSetting.objects.first()
    if setting and setting.is_auto_record:
        try:
            News.objects.create(
                headline=f"[LIVE BROADCAST] {session.headline}",
                category="State",
                news_type="PKG",
                reporter=session.reporter,
                district=session.district or session.reporter.district,
                location=session.district or "Ground Zero",
                description=f"Auto-archived live stream broadcast recorded from field reporter {session.reporter.name} on {session.created_at.strftime('%Y-%m-%d %H:%M')}.",
                media_file=session.recorded_file,
                status="Submitted"
            )
        except Exception:
            pass

    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'message': 'Live broadcast recording saved and archived to Media Library!'
    })



