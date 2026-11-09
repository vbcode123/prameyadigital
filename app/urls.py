from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # 1. Authentication / Login URLs (Admin, Reporter & Desk)
    # ==========================================
    path('', views.login_view, name='login_home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reporter/logout/', views.reporter_logout_view, name='reporter_logout'),
    path('desk/logout/', views.desk_logout_view, name='desk_logout'),
    path('social-media/logout/', views.social_media_logout_view, name='social_media_logout'),
    path('graphic-designer/logout/', views.graphic_designer_logout_view, name='graphic_designer_logout'),
    path('input/logout/', views.input_logout_view, name='input_logout'),
    path('voice-over/logout/', views.voice_over_logout_view, name='voice_over_logout'),
    path('copy-editor/logout/', views.copy_editor_logout_view, name='copy_editor_logout'),
    path('visual-editor/logout/', views.visual_editor_logout_view, name='visual_editor_logout'),
    path('api/heartbeat/', views.heartbeat_api, name='heartbeat_api'),

    # ==========================================
    # 2. Admin Dashboard & Profile
    # ==========================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),

    # ==========================================
    # 3. Reporter Management URLs (Admin Control)
    # ==========================================
    path('reporters/', views.reporter_list_view, name='reporter_list'),
    path('reporters/add/', views.reporter_add_view, name='reporter_add'),
    path('reporters/view/<int:pk>/', views.reporter_detail_view, name='reporter_view'),
    path('reporters/edit/<int:pk>/', views.reporter_edit_view, name='reporter_edit'),
    path('reporters/delete/<int:pk>/', views.reporter_delete_view, name='reporter_delete'),

    # ==========================================
    # 4. Desk Management URLs (Admin Control)
    # ==========================================
    path('desks/', views.desk_list_view, name='desk_list'),
    path('desks/add/', views.desk_add_view, name='desk_add'),
    path('desks/view/<int:pk>/', views.desk_detail_view, name='desk_view'),
    path('desks/edit/<int:pk>/', views.desk_edit_view, name='desk_edit'),
    path('desks/delete/<int:pk>/', views.desk_delete_view, name='desk_delete'),

    # ==========================================
    # 4b. Social Media Management URLs (Admin Control)
    # ==========================================
    path('social-media/', views.social_media_list_view, name='social_media_list'),
    path('social-media/add/', views.social_media_add_view, name='social_media_add'),
    path('social-media/view/<int:pk>/', views.social_media_detail_view, name='social_media_view'),
    path('social-media/edit/<int:pk>/', views.social_media_edit_view, name='social_media_edit'),
    path('social-media/delete/<int:pk>/', views.social_media_delete_view, name='social_media_delete'),

    # ==========================================
    # 4c. Graphic Designer Management URLs (Admin Control)
    # ==========================================
    path('graphic-designers/', views.graphic_designer_list_view, name='graphic_designer_list'),
    path('graphic-designers/add/', views.graphic_designer_add_view, name='graphic_designer_add'),
    path('graphic-designers/view/<int:pk>/', views.graphic_designer_detail_view, name='graphic_designer_view'),
    path('graphic-designers/edit/<int:pk>/', views.graphic_designer_edit_view, name='graphic_designer_edit'),
    path('graphic-designers/delete/<int:pk>/', views.graphic_designer_delete_view, name='graphic_designer_delete'),

    # ==========================================
    # 4d. Input Management URLs (Admin Control)
    # ==========================================
    path('inputs/', views.input_list_view, name='input_list'),
    path('inputs/add/', views.input_add_view, name='input_add'),
    path('inputs/view/<int:pk>/', views.input_detail_view, name='input_view'),
    path('inputs/edit/<int:pk>/', views.input_edit_view, name='input_edit'),
    path('inputs/delete/<int:pk>/', views.input_delete_view, name='input_delete'),

    # ==========================================
    # 4e. Voice Over Management URLs (Admin Control)
    # ==========================================
    path('voice-overs/', views.voice_over_list_view, name='voice_over_list'),
    path('voice-overs/add/', views.voice_over_add_view, name='voice_over_add'),
    path('voice-overs/view/<int:pk>/', views.voice_over_detail_view, name='voice_over_view'),
    path('voice-overs/edit/<int:pk>/', views.voice_over_edit_view, name='voice_over_edit'),
    path('voice-overs/delete/<int:pk>/', views.voice_over_delete_view, name='voice_over_delete'),

    # ==========================================
    # 4f. Copy Editor Management URLs (Admin Control)
    # ==========================================
    path('copy-editors/', views.copy_editor_list_view, name='copy_editor_list'),
    path('copy-editors/add/', views.copy_editor_add_view, name='copy_editor_add'),
    path('copy-editors/view/<int:pk>/', views.copy_editor_detail_view, name='copy_editor_view'),
    path('copy-editors/edit/<int:pk>/', views.copy_editor_edit_view, name='copy_editor_edit'),
    path('copy-editors/delete/<int:pk>/', views.copy_editor_delete_view, name='copy_editor_delete'),

    # ==========================================
    # 4g. Visual Editor Management URLs (Admin Control)
    # ==========================================
    path('visual-editors/', views.visual_editor_list_view, name='visual_editor_list'),
    path('visual-editors/add/', views.visual_editor_add_view, name='visual_editor_add'),
    path('visual-editors/view/<int:pk>/', views.visual_editor_detail_view, name='visual_editor_view'),
    path('visual-editors/edit/<int:pk>/', views.visual_editor_edit_view, name='visual_editor_edit'),
    path('visual-editors/delete/<int:pk>/', views.visual_editor_delete_view, name='visual_editor_delete'),

    # ==========================================
    # 5. Reporter Portal URLs (Reporter Access)
    # ==========================================
    path('reporter/dashboard/', views.reporter_dashboard_view, name='reporter_dashboard'),
    path('reporter/live/', views.reporter_live_view, name='reporter_live'),
    path('reporter/profile/', views.reporter_profile_view, name='reporter_profile'),
    path('reporter/teleprompter/', views.reporter_teleprompter_view, name='reporter_teleprompter'),
    path('reporter/teleprompter/<int:pk>/', views.reporter_teleprompter_view, name='reporter_teleprompter_detail'),
    path('reporter/chat/', views.reporter_chat_desk_view, name='reporter_chat_desk'),
    path('reporter/chat/<int:desk_id>/', views.reporter_chat_desk_view, name='reporter_chat_desk_with_desk'),
    path('reporter/chat/<int:desk_id>/send/', views.reporter_send_chat_message_view, name='reporter_send_chat_message'),
    path('reporter/chat/<int:desk_id>/api/', views.reporter_get_chat_messages_api, name='reporter_get_chat_messages_api'),

    # ==========================================
    # 6. Desk Portal URLs (Desk Staff Access)
    # ==========================================
    path('desk/dashboard/', views.desk_dashboard_view, name='desk_dashboard'),
    path('desk/my-word/', views.desk_my_word_view, name='desk_my_word'),
    path('desk/my-work/', views.desk_my_word_view, name='desk_my_work'),
    path('desk/my-work-list/', views.desk_my_work_list_view, name='desk_my_work_list'),
    path('desk/news/<int:pk>/assign/', views.desk_assign_story_view, name='desk_assign_story'),
    path('desk/studio/<int:pk>/', views.visual_editor_studio_view, name='desk_studio'),
    path('desk/profile/', views.desk_profile_view, name='desk_profile'),
    path('desk/teleprompter/', views.desk_teleprompter_view, name='desk_teleprompter'),
    path('desk/teleprompter/delete/<int:pk>/', views.desk_teleprompter_delete_view, name='desk_teleprompter_delete'),
    path('desk/chat/', views.desk_chat_visual_editor_view, name='desk_chat_visual_editor'),
    path('desk/chat/<int:ve_id>/', views.desk_chat_visual_editor_view, name='desk_chat_visual_editor_with_ve'),
    path('desk/chat/<int:ve_id>/send/', views.desk_send_chat_message_view, name='desk_send_chat_message'),
    path('desk/chat/<int:ve_id>/api/', views.desk_get_chat_messages_api, name='desk_get_chat_messages_api'),
    path('desk/chat-copy-editor/', views.desk_chat_copy_editor_view, name='desk_chat_copy_editor'),
    path('desk/chat-copy-editor/<int:ce_id>/', views.desk_chat_copy_editor_view, name='desk_chat_copy_editor_with_ce'),
    path('desk/chat-copy-editor/<int:ce_id>/send/', views.desk_send_copy_chat_message_view, name='desk_send_copy_chat_message'),
    path('desk/chat-copy-editor/<int:ce_id>/api/', views.desk_get_copy_chat_messages_api, name='desk_get_copy_chat_messages_api'),
    path('desk/chat-voice-over/', views.desk_chat_voice_over_view, name='desk_chat_voice_over'),
    path('desk/chat-voice-over/<int:vo_id>/', views.desk_chat_voice_over_view, name='desk_chat_voice_over_with_vo'),
    path('desk/chat-voice-over/<int:vo_id>/send/', views.desk_send_voice_over_chat_message_view, name='desk_send_voice_over_chat_message'),
    path('desk/chat-voice-over/<int:vo_id>/api/', views.desk_get_voice_over_chat_messages_api, name='desk_get_voice_over_chat_messages_api'),
    path('desk/chat-social-media/', views.desk_chat_social_media_view, name='desk_chat_social_media'),
    path('desk/chat-social-media/<int:sm_id>/', views.desk_chat_social_media_view, name='desk_chat_social_media_with_sm'),
    path('desk/chat-social-media/<int:sm_id>/send/', views.desk_send_social_media_chat_message_view, name='desk_send_social_media_chat_message'),
    path('desk/chat-social-media/<int:sm_id>/api/', views.desk_get_social_media_chat_messages_api, name='desk_get_social_media_chat_messages_api'),
    path('desk/chat-reporter/', views.desk_chat_reporter_view, name='desk_chat_reporter'),
    path('desk/chat-reporter/<int:reporter_id>/', views.desk_chat_reporter_view, name='desk_chat_reporter_with_reporter'),
    path('desk/chat-reporter/<int:reporter_id>/send/', views.desk_send_reporter_chat_message_view, name='desk_send_reporter_chat_message'),
    path('desk/chat-reporter/<int:reporter_id>/api/', views.desk_get_reporter_chat_messages_api, name='desk_get_reporter_chat_messages_api'),

    # ==========================================
    # 6b. Social Media Portal URLs (Social Media Staff Access)
    # ==========================================
    path('social-media/dashboard/', views.social_media_dashboard_view, name='social_media_dashboard'),
    path('social-media/live-control/', views.social_media_live_control_view, name='social_media_live_control'),
    path('social-media/live-settings/', views.social_media_live_settings_view, name='social_media_live_settings'),
    path('social-media/my-task/', views.social_media_my_task_view, name='social_media_my_task'),
    path('social-media/tasks/', views.social_media_my_task_view, name='social_media_tasks'),
    path('social-media/profile/', views.social_media_profile_view, name='social_media_profile'),
    path('social-media/chat/', views.social_media_chat_desk_view, name='social_media_chat_desk'),
    path('social-media/chat/<int:desk_id>/', views.social_media_chat_desk_view, name='social_media_chat_desk_with_desk'),
    path('social-media/chat/<int:desk_id>/send/', views.social_media_send_chat_message_view, name='social_media_send_chat_message'),
    path('social-media/chat/<int:desk_id>/api/', views.social_media_get_chat_messages_api, name='social_media_get_chat_messages_api'),

    # ==========================================
    # 6c. Graphic Designer Portal URLs (Graphic Designer Staff Access)
    # ==========================================
    path('graphic-designer/dashboard/', views.graphic_designer_dashboard_view, name='graphic_designer_dashboard'),
    path('graphic-designer/my-task/', views.graphic_designer_my_task_view, name='graphic_designer_my_task'),
    path('graphic-designer/tasks/', views.graphic_designer_my_task_view, name='graphic_designer_tasks'),
    path('graphic-designer/my-work-list/', views.graphic_designer_my_work_list_view, name='graphic_designer_my_work_list'),
    path('graphic-designer/task/<int:pk>/upload-graphics/', views.graphic_designer_upload_graphics_view, name='graphic_designer_upload_graphics'),
    path('graphic-designer/task/<int:pk>/send-to-visual-editor/', views.graphic_designer_send_to_visual_editor_view, name='graphic_designer_send_to_visual_editor'),
    path('graphic-designer/task/<int:pk>/recall/', views.graphic_designer_recall_task_view, name='graphic_designer_recall_task'),
    path('graphic-designer/ai-generate-image/', views.graphic_designer_generate_ai_image_view, name='graphic_designer_generate_ai_image'),
    path('graphic-designer/task/<int:pk>/save-ai-image/', views.graphic_designer_save_ai_image_to_story_view, name='graphic_designer_save_ai_image'),
    path('graphic-designer/media/<int:pk>/delete/', views.graphic_designer_delete_media_view, name='graphic_designer_delete_media'),
    path('graphic-designer/profile/', views.graphic_designer_profile_view, name='graphic_designer_profile'),
    # Underscore aliases for convenience
    path('graphic_designer/dashboard/', views.graphic_designer_dashboard_view),
    path('graphic_designer/my_task/', views.graphic_designer_my_task_view),
    path('graphic_designer/tasks/', views.graphic_designer_my_task_view),
    path('graphic_designer/my_work_list/', views.graphic_designer_my_work_list_view),
    path('graphic_designer/task/<int:pk>/upload-graphics/', views.graphic_designer_upload_graphics_view),
    path('graphic_designer/task/<int:pk>/send-to-visual-editor/', views.graphic_designer_send_to_visual_editor_view),
    path('graphic_designer/task/<int:pk>/recall/', views.graphic_designer_recall_task_view),
    path('graphic_designer/ai-generate-image/', views.graphic_designer_generate_ai_image_view),
    path('graphic_designer/task/<int:pk>/save-ai-image/', views.graphic_designer_save_ai_image_to_story_view),
    path('graphic_designer/media/<int:pk>/delete/', views.graphic_designer_delete_media_view),
    path('graphic_designer/profile/', views.graphic_designer_profile_view),

    # ==========================================
    # 6d. Input Portal URLs (Input Staff Access)
    # ==========================================
    path('input/dashboard/', views.input_dashboard_view, name='input_dashboard'),
    path('input/profile/', views.input_profile_view, name='input_profile'),
    path('input/news/', views.input_news_verify_list_view, name='input_news_list'),
    path('input/news/verify/', views.input_news_verify_list_view, name='input_news_verify_list'),
    path('input/news/<int:pk>/status/', views.input_update_news_status_view, name='input_update_news_status'),
    path('input/news/download-zip/', views.input_download_approved_news_zip_view, name='input_download_approved_zip'),

    # ==========================================
    # 6e. Voice Over Portal URLs (Voice Over Staff Access)
    # ==========================================
    path('voice-over/dashboard/', views.voice_over_dashboard_view, name='voice_over_dashboard'),
    path('voice-over/my-task/', views.voice_over_my_task_view, name='voice_over_my_task'),
    path('voice-over/tasks/', views.voice_over_my_task_view, name='voice_over_tasks'),
    path('voice-over/my-work-list/', views.voice_over_my_work_list_view, name='voice_over_my_work_list'),
    path('voice-over/task/<int:pk>/submit-audio/', views.voice_over_submit_audio_view, name='voice_over_submit_audio'),
    path('voice-over/profile/', views.voice_over_profile_view, name='voice_over_profile'),
    path('voice-over/chat/', views.voice_over_chat_desk_view, name='voice_over_chat_desk'),
    path('voice-over/chat/<int:desk_id>/', views.voice_over_chat_desk_view, name='voice_over_chat_desk_with_desk'),
    path('voice-over/chat/<int:desk_id>/send/', views.voice_over_send_chat_message_view, name='voice_over_send_chat_message'),
    path('voice-over/chat/<int:desk_id>/api/', views.voice_over_get_chat_messages_api, name='voice_over_get_chat_messages_api'),

    # ==========================================
    # 6f. Copy Editor Portal URLs (Copy Editor Staff Access)
    # ==========================================
    path('copy-editor/dashboard/', views.copy_editor_dashboard_view, name='copy_editor_dashboard'),
    path('copy-editor/my-task/', views.copy_editor_my_task_view, name='copy_editor_my_task'),
    path('copy-editor/tasks/', views.copy_editor_my_task_view, name='copy_editor_tasks'),
    path('copy-editor/my-task-list/', views.copy_editor_my_task_list_view, name='copy_editor_my_task_list'),
    path('copy-editor/my-work-list/', views.copy_editor_my_task_list_view, name='copy_editor_my_work_list'),
    path('copy-editor/task/<int:pk>/edit-script/', views.copy_editor_edit_script_view, name='copy_editor_edit_script'),
    path('copy-editor/profile/', views.copy_editor_profile_view, name='copy_editor_profile'),
    path('copy-editor/chat/', views.copy_editor_chat_desk_view, name='copy_editor_chat_desk'),
    path('copy-editor/chat/<int:desk_id>/', views.copy_editor_chat_desk_view, name='copy_editor_chat_desk_with_desk'),
    path('copy-editor/chat/<int:desk_id>/send/', views.copy_editor_send_chat_message_view, name='copy_editor_send_chat_message'),
    path('copy-editor/chat/<int:desk_id>/api/', views.copy_editor_get_chat_messages_api, name='copy_editor_get_chat_messages_api'),

    # ==========================================
    # 6g. Visual Editor Portal URLs (Visual Editor Staff Access)
    # ==========================================
    path('visual-editor/dashboard/', views.visual_editor_dashboard_view, name='visual_editor_dashboard'),
    path('visual-editor/my-task/', views.visual_editor_my_task_view, name='visual_editor_my_task'),
    path('visual-editor/tasks/', views.visual_editor_my_task_view, name='visual_editor_tasks'),
    path('visual-editor/studio/<int:pk>/', views.visual_editor_studio_view, name='visual_editor_studio'),
    path('visual-editor/studio/<int:pk>/save/', views.save_edited_video_view, name='save_edited_video'),
    path('visual-editor/profile/', views.visual_editor_profile_view, name='visual_editor_profile'),
    path('visual-editor/chat/', views.visual_editor_chat_desk_view, name='visual_editor_chat_desk'),
    path('visual-editor/chat/<int:desk_id>/', views.visual_editor_chat_desk_view, name='visual_editor_chat_desk_with_desk'),
    path('visual-editor/chat/<int:desk_id>/send/', views.visual_editor_send_chat_message_view, name='visual_editor_send_chat_message'),
    path('visual-editor/chat/<int:desk_id>/api/', views.visual_editor_get_chat_messages_api, name='visual_editor_get_chat_messages_api'),


    # ==========================================
    # 7. News Management URLs (Reporter, Admin & Desk)
    # ==========================================
    path('news/', views.news_list_view, name='news_list'),
    path('news/add/', views.news_add_view, name='news_add'),
    path('news/view/<int:pk>/', views.news_detail_view, name='news_view'),
    path('news/edit/<int:pk>/', views.news_edit_view, name='news_edit'),
    path('news/delete/<int:pk>/', views.news_delete_view, name='news_delete'),
    path('news/ai-check/', views.ai_check_script_view, name='news_ai_check'),
    path('news/<int:pk>/download-media/', views.news_download_single_media_view, name='news_download_media'),

    # Convenient portal aliases
    path('reporter/news/', views.news_list_view, name='reporter_news_list'),
    path('reporter/news/add/', views.news_add_view, name='reporter_news_add'),
    path('input/news/<int:pk>/download/', views.news_download_single_media_view, name='input_download_single_news'),
    path('desk/news/', views.desk_news_verify_list_view, name='desk_news_list'),
    path('desk/news/verify/', views.desk_news_verify_list_view, name='desk_news_verify_list'),
    path('desk/news/<int:pk>/status/', views.desk_update_news_status_view, name='desk_update_news_status'),
    path('desk/news/<int:pk>/download/', views.news_download_single_media_view, name='desk_download_single_news'),
    path('desk/news/download-zip/', views.desk_download_approved_news_zip_view, name='desk_download_approved_zip'),

    # ==========================================
    # 8. Media Download Approval Guard URLs
    # ==========================================
    path('api/media-download/request/', views.request_download_passcode_view, name='request_download_passcode'),
    path('api/media-download/verify/', views.verify_download_passcode_view, name='verify_download_passcode'),
    path('api/media-download/status/', views.check_download_status_view, name='check_download_status'),
    path('api/media-download/admin-requests/', views.admin_download_requests_api, name='admin_download_requests_api'),
    path('admin-download-approvals/', views.admin_download_approvals_view, name='admin_download_approvals'),

    # ==========================================
    # 9. Real-time Live Broadcast APIs
    # ==========================================
    path('api/live/request/', views.api_reporter_request_live, name='api_reporter_request_live'),
    path('api/live/status/<int:session_id>/', views.api_reporter_poll_status, name='api_reporter_poll_status'),
    path('api/live/pending-requests/', views.api_social_pending_requests, name='api_social_pending_requests'),
    path('api/live/approve/', views.api_social_approve_live, name='api_social_approve_live'),
    path('api/live/cue/', views.api_social_send_cue, name='api_social_send_cue'),
    path('api/live/stop/', views.api_social_stop_live, name='api_social_stop_live'),
    path('api/live/stream-chunk/', views.api_live_stream_chunk, name='api_live_stream_chunk'),
    path('api/live/relay-status/<int:session_id>/', views.api_live_relay_status, name='api_live_relay_status'),
    path('api/live/save-recording/', views.api_live_save_recording, name='api_live_save_recording'),
]

