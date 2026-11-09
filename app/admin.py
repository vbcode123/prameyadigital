from django.contrib import admin
from .models import Reporter, Desk, SocialMedia, GraphicDesigner, InputUser, VoiceOverUser, CopyEditor, VisualEditor, News, NewsMedia

admin.site.site_header = "Prameya Digital Administration"
admin.site.site_title = "Prameya Digital Portal"
admin.site.index_title = "Welcome to Prameya Digital Newsroom"


class NewsMediaInline(admin.TabularInline):
    model = NewsMedia
    extra = 1


@admin.register(Reporter)
class ReporterAdmin(admin.ModelAdmin):
    list_display = ('reporter_id', 'name', 'phone_number', 'district', 'is_active', 'created_at')
    list_filter = ('district', 'is_active', 'created_at')
    search_fields = ('reporter_id', 'name', 'phone_number', 'district', 'address')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Desk)
class DeskAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number', 'email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SocialMedia)
class SocialMediaAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GraphicDesigner)
class GraphicDesignerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(InputUser)
class InputUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VoiceOverUser)
class VoiceOverUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CopyEditor)
class CopyEditorAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VisualEditor)
class VisualEditorAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('headline', 'news_type', 'category', 'district', 'reporter', 'status', 'created_at')
    list_filter = ('news_type', 'category', 'district', 'status', 'created_at')
    search_fields = ('headline', 'description', 'location', 'district', 'byte_interview')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [NewsMediaInline]


@admin.register(NewsMedia)
class NewsMediaAdmin(admin.ModelAdmin):
    list_display = ('news', 'file', 'caption', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('news__headline', 'caption')


from .models import DeskSocialChatMessage, LiveStreamSetting, LiveBroadcastSession


@admin.register(LiveStreamSetting)
class LiveStreamSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'youtube_rtmp_url', 'is_auto_record', 'updated_at')


@admin.register(LiveBroadcastSession)
class LiveBroadcastSessionAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'headline', 'district', 'status', 'destination', 'started_at', 'created_at')
    list_filter = ('status', 'destination', 'created_at')
    search_fields = ('reporter__name', 'headline', 'district')


@admin.register(DeskSocialChatMessage)
class DeskSocialChatMessageAdmin(admin.ModelAdmin):
    list_display = ('desk', 'social_media', 'sender_type', 'message', 'is_read', 'created_at')
    list_filter = ('sender_type', 'is_read', 'created_at')
    search_fields = ('desk__name', 'social_media__name', 'message')


