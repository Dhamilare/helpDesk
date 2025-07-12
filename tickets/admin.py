from django.contrib import admin
from .models import (
    Department, Category, Priority, UserProfile,
    Ticket, TicketComment, TicketAttachment, TicketHistory,
    KnowledgeBase, SLA
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'is_active')
    search_fields = ('name',)
    list_filter = ('department', 'is_active')


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'response_time')
    ordering = ('level',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'job_title', 'is_agent', 'is_supervisor')
    list_filter = ('department', 'is_agent', 'is_supervisor')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'title', 'department', 'category', 'priority', 'status', 'created_at', 'due_date')
    search_fields = ('ticket_number', 'title')
    list_filter = ('status', 'department', 'priority')
    date_hierarchy = 'created_at'
    readonly_fields = ('ticket_number',)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'ticket', 'uploaded_by', 'uploaded_at', 'file_size')
    readonly_fields = ('file_size',)


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'action', 'field_changed', 'timestamp')
    search_fields = ('ticket__ticket_number', 'user__username', 'action')


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'is_published', 'views', 'created_at')
    search_fields = ('title', 'tags')
    list_filter = ('category', 'is_published')


@admin.register(SLA)
class SLAAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'priority', 'response_time', 'resolution_time', 'is_active')
    list_filter = ('department', 'priority', 'is_active')
