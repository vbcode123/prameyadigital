from django.db import models
from django.contrib.auth.models import User


def generate_next_reporter_id():
    """
    Generates the next unique Reporter ID in the format PD_<number>,
    starting at PD_1001 or incrementing from the highest existing PD_ or NL_ number.
    """
    reporters = Reporter.objects.filter(
        models.Q(reporter_id__startswith='PD_') | models.Q(reporter_id__startswith='NL_')
    )
    max_num = 1000
    for r in reporters:
        if r.reporter_id:
            suffix = r.reporter_id[3:].strip()
            if suffix.isdigit():
                val = int(suffix)
                if val > max_num:
                    max_num = val
    return f"PD_{max_num + 1}"


_ACTIVE_PRESENCE_CACHE = {
    'timestamp': 0,
    'user_ids': set(),
}
_ACTIVE_USERS_CACHE = _ACTIVE_PRESENCE_CACHE
EXPLICITLY_LOGGED_OUT = {}  # user_id -> datetime of explicit sign-out


def get_active_session_info():
    """
    Returns cached active presence set: user_ids
    from active unexpired sessions in Django.
    Cached for 5 seconds to eliminate database overhead while remaining real-time.
    """
    import time
    from django.utils import timezone
    from django.contrib.sessions.models import Session

    now_ts = time.time()
    if now_ts - _ACTIVE_PRESENCE_CACHE.get('timestamp', 0) < 5:
        return _ACTIVE_PRESENCE_CACHE

    active_ids = set()

    try:
        now = timezone.now()
        # Query unexpired sessions; fallback gracefully if timezone comparison behaves unexpectedly
        try:
            sessions = Session.objects.filter(expire_date__gt=now)
        except Exception:
            sessions = Session.objects.all()

        for s in sessions:
            try:
                # Check expire_date safely
                if s.expire_date:
                    if timezone.is_aware(s.expire_date):
                        if s.expire_date <= now:
                            continue
                    else:
                        if s.expire_date <= timezone.localtime(now).replace(tzinfo=None):
                            continue

                data = s.get_decoded()
                uid = data.get('_auth_user_id')
                if uid:
                    active_ids.add(int(uid))
            except Exception:
                continue
    except Exception:
        pass

    _ACTIVE_PRESENCE_CACHE['timestamp'] = now_ts
    _ACTIVE_PRESENCE_CACHE['user_ids'] = active_ids
    return _ACTIVE_PRESENCE_CACHE


def get_active_session_user_ids():
    """Backward compatibility helper"""
    return get_active_session_info()['user_ids']


def compute_profile_last_seen_info(profile):
    """
    Computes real-time online status and human-readable last seen text in local time (Asia/Kolkata).
    A profile is ONLY Online if:
    1. The profile's associated user account has an active, unexpired login session (is logged in).
    2. The user has not explicitly logged out.
    3. The user has recent activity (last_seen within 300 seconds / 5 minutes, or recent login).
    If the user has NOT logged in, they are ALWAYS Offline!
    """
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    last = getattr(profile, 'last_seen', None)
    user = getattr(profile, 'user', None)

    # 1. Fallback to user.last_login if profile last_seen is not set or older
    if user:
        user_last_login = getattr(user, 'last_login', None)
        if user_last_login and (not last or user_last_login > last):
            last = user_last_login

    # 2. Check active session: ONLY this user's specific account ID
    is_in_active_session = False
    if user:
        active_uids = get_active_session_info().get('user_ids', set())
        if user.pk in active_uids:
            is_in_active_session = True

    # 3. Check explicit logout
    is_logged_out = False
    if user:
        logout_ts = EXPLICITLY_LOGGED_OUT.get(user.pk)
        if logout_ts:
            if last and last > logout_ts:
                EXPLICITLY_LOGGED_OUT.pop(user.pk, None)
            else:
                is_logged_out = True

    # 4. Determine Online vs Offline:
    # A user MUST BE in an active session (LOGGED IN) to be Online!
    is_online = False
    if is_in_active_session and not is_logged_out:
        if last:
            diff = (now - last).total_seconds()
            # Active within 5 minutes (300s) while logged in
            if -60 <= diff < 300:
                is_online = True
            # Allow up to 10 minutes (600s) if user recently logged in
            elif -60 <= diff < 600:
                is_online = True
        else:
            # Active session with no last_seen recorded yet -> Online
            is_online = True

    if is_online:
        return {'is_online': True, 'text': 'Online'}

    if not last:
        return {'is_online': False, 'text': 'Offline'}

    # Convert to local timezone for accurate display in India (Asia/Kolkata)
    local_last = timezone.localtime(last) if timezone.is_aware(last) else last
    local_now = timezone.localtime(now) if timezone.is_aware(now) else now

    time_str = local_last.strftime('%I:%M %p')
    if local_last.date() == local_now.date():
        return {'is_online': False, 'text': f"Last seen today at {time_str}"}
    elif local_last.date() == (local_now - timedelta(days=1)).date():
        return {'is_online': False, 'text': f"Last seen yesterday at {time_str}"}
    else:
        return {'is_online': False, 'text': f"Last seen on {local_last.strftime('%d %b, %I:%M %p')}"}



class OnlineStatusMixin:
    """
    Mixin providing real-time online status and human-readable last seen text
    with property getters and setters so views can assign pre-computed values without AttributeError.
    """
    def get_last_seen_info(self):
        return compute_profile_last_seen_info(self)

    @property
    def is_online(self):
        if hasattr(self, '_is_online'):
            return bool(self._is_online)
        return bool(self.get_last_seen_info().get('is_online'))

    @is_online.setter
    def is_online(self, value):
        self._is_online = bool(value)

    @property
    def last_seen_text(self):
        if hasattr(self, '_last_seen_text'):
            return self._last_seen_text
        return self.get_last_seen_info().get('text', '')

    @last_seen_text.setter
    def last_seen_text(self, value):
        self._last_seen_text = value


class Reporter(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reporter_profile')
    reporter_id = models.CharField(
        max_length=30, 
        unique=True, 
        blank=True, 
        null=True, 
        db_index=True, 
        help_text="Official Reporter ID (e.g. PD_1001)"
    )
    name = models.CharField(max_length=150, help_text="Full Name of the Reporter")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    address = models.TextField(help_text="Full Residential / Office Address")
    district = models.CharField(max_length=100, help_text="Assigned District / Location")
    aadhar_image = models.ImageField(upload_to='aadhar_images/', blank=True, null=True, help_text="Aadhar Card Document Image")
    profile_image = models.ImageField(upload_to='reporter_profiles/', blank=True, null=True, help_text="Reporter Passport/Profile Photo")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last active timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reporter"
        verbose_name_plural = "Reporters"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reporter_id:
            self.reporter_id = generate_next_reporter_id()
        super().save(*args, **kwargs)

    def __str__(self):
        rep_id = f" [{self.reporter_id}]" if self.reporter_id else ""
        return f"{self.name}{rep_id} ({self.district} - {self.phone_number})"


class Desk(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='desk_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Desk Staff")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    email = models.EmailField(max_length=255, unique=True, help_text="Gmail / Email Address")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last active timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Desk"
        verbose_name_plural = "Desks"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class SocialMedia(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='social_media_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Social Media Staff")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last active timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Social Media"
        verbose_name_plural = "Social Media Staff"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class GraphicDesigner(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='graphic_designer_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Graphic Designer")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Graphic Designer"
        verbose_name_plural = "Graphic Designers"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class InputUser(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='input_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Input Staff")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Input"
        verbose_name_plural = "Inputs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


# Convenient alias
Input = InputUser


class VoiceOverUser(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='voice_over_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Voice Over Staff")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last active timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voice Over"
        verbose_name_plural = "Voice Overs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


# Convenient aliases
VoiceOver = VoiceOverUser
VoiceHover = VoiceOverUser


class CopyEditor(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='copy_editor_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Copy Editor")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last active timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Copy Editor"
        verbose_name_plural = "Copy Editors"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class VisualEditor(OnlineStatusMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='visual_editor_profile')
    name = models.CharField(max_length=150, help_text="Full Name of the Visual Editor")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Login Phone Number")
    is_active = models.BooleanField(default=True, help_text="Account Active Status")
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Last active timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Visual Editor"
        verbose_name_plural = "Visual Editors"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


NEWS_TYPE_CHOICES = [
    ('AVO', 'AVO'),
    ('Byte', 'Byte'),
    ('AVO Byte', 'AVO Byte'),
    ('PKG', 'PKG'),
]

NEWS_CATEGORY_CHOICES = [
    ('Breaking News', 'Breaking News'),
    ('Politics', 'Politics'),
    ('Crime & Law', 'Crime & Law'),
    ('Accident & Disaster', 'Accident & Disaster'),
    ('Local & Regional', 'Local & Regional'),
    ('Development & Infra', 'Development & Infra'),
    ('Sports', 'Sports'),
    ('Entertainment', 'Entertainment'),
    ('Business & Economy', 'Business & Economy'),
    ('Health & Education', 'Health & Education'),
    ('General', 'General'),
]

NEWS_STATUS_CHOICES = [
    ('Submitted', 'Submitted'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected'),
]


class News(models.Model):
    headline = models.CharField(max_length=300, help_text="News Headline / Title")
    news_type = models.CharField(max_length=50, choices=NEWS_TYPE_CHOICES, help_text="News Format Type")
    category = models.CharField(max_length=100, choices=NEWS_CATEGORY_CHOICES, default='General')
    location = models.CharField(max_length=200, help_text="Incident Location / Landmark")
    district = models.CharField(max_length=100, help_text="Assigned District")
    description = models.TextField(help_text="Detailed News Description / Script")
    media_file = models.FileField(upload_to='news_media/', blank=True, null=True, help_text="Main Video or Image File")
    byte_interview = models.TextField(blank=True, null=True, help_text="Optional Byte / Interview Details")
    byte_media = models.FileField(upload_to='news_bytes/', blank=True, null=True, help_text="Optional Byte Audio / Video File")
    reporter = models.ForeignKey(Reporter, on_delete=models.SET_NULL, null=True, blank=True, related_name='news_reports')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_news')
    # Studio & Editing fields
    edited_video = models.FileField(upload_to='edited_news_videos/', blank=True, null=True, help_text="Final rendered news video from Studio")
    is_video_edited_by_desk = models.BooleanField(default=False, help_text="True if Desk staff edited the video")
    edited_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when video was edited in studio")

    # Team Assignment fields
    assigned_copy_editor = models.ForeignKey(CopyEditor, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_news')
    edited_by_copy_editor = models.ForeignKey(CopyEditor, on_delete=models.SET_NULL, null=True, blank=True, related_name='script_edited_news', help_text="Copy Editor who edited and saved the script")
    is_script_edited_by_copy_editor = models.BooleanField(default=False, help_text="True if Copy Editor has edited and saved/forwarded script")
    script_edited_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when Copy Editor saved script")
    sent_to_visual_editor_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when Copy Editor forwarded script to Visual Editor")
    assigned_visual_editor = models.ForeignKey(VisualEditor, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_news')
    assigned_voice_over = models.ForeignKey(VoiceOverUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_news')
    assigned_graphic_designer = models.ForeignKey(GraphicDesigner, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_news')
    is_graphics_completed = models.BooleanField(default=False, help_text="True if Graphic Designer has prepared graphics and sent to Visual Editor")
    graphics_sent_to_visual_editor_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when Graphic Designer sent graphics to Visual Editor")
    desk_notes = models.TextField(blank=True, null=True, help_text="Desk instructions to assigned staff")
    assigned_at = models.DateTimeField(null=True, blank=True)

    # Social Media Dispatch
    assigned_social_media = models.ForeignKey(SocialMedia, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_news')
    sent_to_social_media = models.BooleanField(default=False, help_text="True if story is sent to Social Media team")
    sent_to_social_media_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=NEWS_STATUS_CHOICES, default='Submitted')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "News"
        verbose_name_plural = "News"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.status == 'Rejected':
            # Delete media files from storage when story is rejected
            if self.media_file:
                try:
                    self.media_file.delete(save=False)
                except Exception:
                    pass
                self.media_file = None
            if self.byte_media:
                try:
                    self.byte_media.delete(save=False)
                except Exception:
                    pass
                self.byte_media = None
            if self.pk:
                for extra in self.additional_media.all():
                    try:
                        extra.file.delete(save=False)
                    except Exception:
                        pass
                    extra.delete()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.news_type}] {self.headline} ({self.district})"

    @property
    def is_video(self):
        if self.media_file:
            import os
            ext = os.path.splitext(self.media_file.name)[1].lower()
            return ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.3gp', '.m4v']
        return False

    @property
    def is_image(self):
        if self.media_file:
            import os
            ext = os.path.splitext(self.media_file.name)[1].lower()
            return ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg']
        return False

    @property
    def total_media_count(self):
        count = 1 if self.media_file else 0
        if self.pk:
            count += self.additional_media.count()
        return count

    @property
    def byte_is_video(self):
        if self.byte_media:
            import os
            ext = os.path.splitext(self.byte_media.name)[1].lower()
            return ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
        return False

    @property
    def byte_is_audio(self):
        if self.byte_media:
            import os
            ext = os.path.splitext(self.byte_media.name)[1].lower()
            return ext in ['.mp3', '.wav', '.ogg', '.m4a', '.aac']
        return False

    @property
    def has_edited_video(self):
        return bool(self.edited_video and hasattr(self.edited_video, 'name') and self.edited_video.name)


class NewsMedia(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='additional_media')
    file = models.FileField(upload_to='news_media/', help_text="Additional Video or Image File")
    caption = models.CharField(max_length=255, blank=True, null=True, help_text="Optional caption or note")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "News Media"
        verbose_name_plural = "News Media Files"
        ordering = ['created_at']

    def __str__(self):
        return f"Media for {self.news.headline} ({self.file.name})"

    @property
    def is_video(self):
        if self.file:
            import os
            ext = os.path.splitext(self.file.name)[1].lower()
            return ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.3gp', '.m4v']
        return False

    @property
    def is_image(self):
        if self.file:
            import os
            ext = os.path.splitext(self.file.name)[1].lower()
            return ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg']
        return False

    @property
    def file_extension(self):
        if self.file:
            import os
            return os.path.splitext(self.file.name)[1].lower().replace('.', '').upper()
        return ''


class TeleprompterScript(models.Model):
    reporter = models.ForeignKey(Reporter, on_delete=models.CASCADE, related_name='teleprompter_scripts')
    desk = models.ForeignKey(Desk, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_teleprompter_scripts')
    title = models.CharField(max_length=255, blank=True, default='', help_text="Headline or Topic of Teleprompter")
    script_text = models.TextField(help_text="Odia, English, or Hindi teleprompter script narrative")
    news = models.ForeignKey(News, on_delete=models.SET_NULL, null=True, blank=True, related_name='teleprompter_scripts')
    is_read = models.BooleanField(default=False, help_text="True if viewed by reporter")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_teleprompterscript'
        verbose_name = "Teleprompter Script"
        verbose_name_plural = "Teleprompter Scripts"
        ordering = ['-created_at']

    def __str__(self):
        rep_name = self.reporter.name if self.reporter else "Reporter"
        return f"Prompter #{self.pk} for {rep_name} - {self.title[:30]}"


class DeskVisualChatMessage(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name='visual_editor_chat_messages')
    visual_editor = models.ForeignKey(VisualEditor, on_delete=models.CASCADE, related_name='desk_chat_messages')
    sender_type = models.CharField(
        max_length=20,
        choices=[('desk', 'Desk'), ('visual_editor', 'Visual Editor')],
        help_text="Sender role: desk or visual_editor"
    )
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_desk_ve_messages')
    message = models.TextField(help_text="Message text content")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, help_text="Optional attached file or image")
    is_read = models.BooleanField(default=False, help_text="True if read by recipient")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_deskvisualchatmessage'
        verbose_name = "Desk-Visual Editor Chat Message"
        verbose_name_plural = "Desk-Visual Editor Chat Messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type.upper()}] {self.desk.name} <-> {self.visual_editor.name}: {self.message[:30]}"


class DeskCopyChatMessage(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name='copy_editor_chat_messages')
    copy_editor = models.ForeignKey(CopyEditor, on_delete=models.CASCADE, related_name='desk_chat_messages')
    sender_type = models.CharField(
        max_length=20,
        choices=[('desk', 'Desk'), ('copy_editor', 'Copy Editor')],
        help_text="Sender role: desk or copy_editor"
    )
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_desk_ce_messages')
    message = models.TextField(help_text="Message text content")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, help_text="Optional attached file or image")
    is_read = models.BooleanField(default=False, help_text="True if read by recipient")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_deskcopychatmessage'
        verbose_name = "Desk-Copy Editor Chat Message"
        verbose_name_plural = "Desk-Copy Editor Chat Messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type.upper()}] {self.desk.name} <-> {self.copy_editor.name}: {self.message[:30]}"


class DeskVoiceOverChatMessage(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name='voice_over_chat_messages')
    voice_over = models.ForeignKey(VoiceOverUser, on_delete=models.CASCADE, related_name='desk_chat_messages')
    sender_type = models.CharField(
        max_length=20,
        choices=[('desk', 'Desk'), ('voice_over', 'Voice Over')],
        help_text="Sender role: desk or voice_over"
    )
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_desk_vo_messages')
    message = models.TextField(help_text="Message text content")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, help_text="Optional attached audio, script, or image")
    is_read = models.BooleanField(default=False, help_text="True if read by recipient")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_deskvoiceoverchatmessage'
        verbose_name = "Desk-Voice Over Chat Message"
        verbose_name_plural = "Desk-Voice Over Chat Messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type.upper()}] {self.desk.name} <-> {self.voice_over.name}: {self.message[:30]}"


class DeskSocialChatMessage(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name='social_media_chat_messages')
    social_media = models.ForeignKey(SocialMedia, on_delete=models.CASCADE, related_name='desk_chat_messages')
    sender_type = models.CharField(
        max_length=20,
        choices=[('desk', 'Desk'), ('social_media', 'Social Media')],
        help_text="Sender role: desk or social_media"
    )
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_desk_sm_messages')
    message = models.TextField(help_text="Message text content")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, help_text="Optional attached file or image")
    is_read = models.BooleanField(default=False, help_text="True if read by recipient")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_desksocialchatmessage'
        verbose_name = "Desk-Social Media Chat Message"
        verbose_name_plural = "Desk-Social Media Chat Messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type.upper()}] {self.desk.name} <-> {self.social_media.name}: {self.message[:30]}"


class DeskReporterChatMessage(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.CASCADE, related_name='reporter_chat_messages')
    reporter = models.ForeignKey(Reporter, on_delete=models.CASCADE, related_name='desk_chat_messages')
    sender_type = models.CharField(
        max_length=20,
        choices=[('desk', 'Desk'), ('reporter', 'Reporter')],
        help_text="Sender role: desk or reporter"
    )
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_desk_rep_messages')
    message = models.TextField(help_text="Message text content")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, help_text="Optional attached file or image")
    is_read = models.BooleanField(default=False, help_text="True if read by recipient")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_deskreporterchatmessage'
        verbose_name = "Desk-Reporter Chat Message"
        verbose_name_plural = "Desk-Reporter Chat Messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type.upper()}] {self.desk.name} <-> {self.reporter.name}: {self.message[:30]}"


class MediaDownloadRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_requests')
    requester_name = models.CharField(max_length=150, help_text="Name of staff requesting download")
    role_name = models.CharField(max_length=50, default='Staff', help_text="Role: Desk, Visual Editor, etc.")
    file_url = models.TextField(help_text="URL of media file being requested")
    file_name = models.CharField(max_length=255, help_text="Clean display name of the file/story")
    passcode = models.CharField(max_length=6, help_text="6-digit auto-generated passcode")
    is_approved = models.BooleanField(default=False, help_text="True if approved by Admin/Chief Editor")
    is_used = models.BooleanField(default=False, help_text="True once successfully downloaded")
    is_rejected = models.BooleanField(default=False, help_text="True if rejected by Admin")
    rejection_reason = models.CharField(max_length=255, blank=True, null=True, help_text="Reason for rejection if provided")
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_downloads')
    rejected_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_downloads')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Expiry time (e.g. +15 mins)")

    class Meta:
        db_table = 'app_mediadownloadrequest'
        verbose_name = "Media Download Request"
        verbose_name_plural = "Media Download Requests"
        ordering = ['-created_at']

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def status_label(self):
        if self.is_used:
            return "Used"
        if getattr(self, 'is_rejected', False):
            return "Rejected"
        if self.is_approved:
            return "Approved"
        if self.is_expired():
            return "Expired"
        return "Pending"

    def __str__(self):
        return f"[{self.passcode}] {self.requester_name} ({self.role_name}) - {self.file_name[:25]} ({self.status_label()})"


# ==========================================
# Live Streaming & Broadcast Models
# ==========================================
class LiveStreamSetting(models.Model):
    """
    Channel-wide Live Streaming Settings (YouTube & Facebook RTMP credentials)
    """
    youtube_rtmp_url = models.CharField(max_length=255, default='rtmp://a.rtmp.youtube.com/live2', help_text="YouTube RTMP Server URL")
    youtube_stream_key = models.CharField(max_length=255, blank=True, null=True, help_text="YouTube Live Stream Key")
    facebook_rtmp_url = models.CharField(max_length=255, default='rtmps://live-api-s.facebook.com:443/rtmp/', help_text="Facebook Live RTMP URL")
    facebook_stream_key = models.CharField(max_length=255, blank=True, null=True, help_text="Facebook Live Stream Key")
    is_auto_record = models.BooleanField(default=True, help_text="Auto-save live stream to media library on finish")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Live Stream Setting"
        verbose_name_plural = "Live Stream Settings"

    def __str__(self):
        yt_status = "Configured" if self.youtube_stream_key else "Missing Key"
        fb_status = "Configured" if self.facebook_stream_key else "Missing Key"
        return f"Live Settings (YT: {yt_status}, FB: {fb_status})"


class LiveBroadcastSession(models.Model):
    """
    Field Reporter Live Broadcast Session with Social Media Gatekeeping
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved / Standby'),
        ('live', 'Live On Air'),
        ('ended', 'Broadcast Ended'),
        ('rejected', 'Rejected / Cancelled'),
    ]

    DESTINATION_CHOICES = [
        ('youtube', 'YouTube Live'),
        ('facebook', 'Facebook Live'),
        ('both', 'YouTube & Facebook'),
        ('internal', 'Internal Preview Only'),
    ]

    BROADCAST_TYPE_CHOICES = [
        ('camera', 'Live Camera Feed'),
        ('recorded', 'Pre-Recorded Video'),
    ]

    reporter = models.ForeignKey(Reporter, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_sessions')
    broadcast_type = models.CharField(max_length=20, choices=BROADCAST_TYPE_CHOICES, default='camera')
    headline = models.CharField(max_length=255, help_text="Live Story Headline / Topic")
    district = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    destination = models.CharField(max_length=20, choices=DESTINATION_CHOICES, default='youtube')
    overlay_graphics = models.BooleanField(default=True, help_text="Burn Logo, LIVE badge and Headline onto stream")
    current_cue = models.CharField(max_length=255, blank=True, null=True, help_text="Live prompter cue from Social Media Desk")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_broadcasts')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    recorded_file = models.FileField(upload_to='live_recordings/', blank=True, null=True, help_text="Saved MP4 recording")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Live Broadcast Session"
        verbose_name_plural = "Live Broadcast Sessions"
        ordering = ['-created_at']

    def __str__(self):
        rep_name = self.reporter.name if self.reporter else "Newsroom Desk"
        return f"[{self.get_status_display()}] {rep_name} ({self.district}) - {self.headline[:30]}"




