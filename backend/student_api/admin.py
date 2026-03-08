# student_api/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'full_name', 'role', 'is_approved', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_approved', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'full_name', 'phone_number')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number', 'college_company', 'address')}),
        ('Permissions', {'fields': ('role', 'is_approved', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2', 'role', 'is_approved', 'is_staff'),
        }),
    )
    
    actions = ['approve_users', 'disapprove_users']
    
    def approve_users(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} users were approved successfully.')
    approve_users.short_description = "Approve selected users"
    
    def disapprove_users(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} users were disapproved.')
    disapprove_users.short_description = "Disapprove selected users"

class ArchitectureAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution_type', 'department_name', 'student_count', 'staff_count', 'created_by', 'is_active', 'created_at')
    list_filter = ('institution_type', 'is_active', 'created_at')
    search_fields = ('name', 'department_name', 'class_name', 'division')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('parent', 'created_by')
    list_per_page = 20
    
    def get_forms_count(self, obj):
        return obj.forms.count()
    get_forms_count.short_description = 'Forms Count'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

class FormAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'architecture', 'is_published', 'is_active', 'get_fields_count', 'get_submissions_count', 'created_at')
    list_filter = ('is_published', 'is_active', 'created_at', 'architecture')
    search_fields = ('title', 'description', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('created_by', 'architecture')
    list_editable = ('is_published', 'is_active')
    list_per_page = 20
    
    def get_fields_count(self, obj):
        return obj.fields.count()
    get_fields_count.short_description = 'Fields'
    
    def get_submissions_count(self, obj):
        return obj.submissions.count()
    get_submissions_count.short_description = 'Submissions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by', 'architecture')

class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 1
    fields = ('label', 'field_type', 'is_required', 'order', 'is_active')
    readonly_fields = ('created_at',)

class FormFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'form', 'field_type', 'is_required', 'order', 'is_active', 'created_at')
    list_filter = ('field_type', 'is_required', 'is_active', 'created_at')
    search_fields = ('label', 'form__title')
    readonly_fields = ('created_at',)
    list_editable = ('order', 'is_active')
    raw_id_fields = ('form',)
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('form')

class FormTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'form', 'architecture', 'is_used', 'used_at', 'created_at')
    list_filter = ('is_used', 'created_at', 'architecture')
    search_fields = ('token', 'form__title', 'architecture__name')
    readonly_fields = ('created_at', 'used_at')
    raw_id_fields = ('form', 'architecture')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('form', 'architecture')

class FieldResponseInline(admin.TabularInline):
    model = FieldResponse
    extra = 0
    readonly_fields = ('field', 'get_value_display', 'created_at')
    can_delete = False
    max_num = 0
    
    def get_value_display(self, obj):
        return obj.get_value() or "No value"
    get_value_display.short_description = 'Value'
    
    def has_add_permission(self, request, obj):
        return False

class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'form', 'student', 'token', 'get_responses_count', 'submitted_at')
    list_filter = ('submitted_at', 'form')
    search_fields = ('form__title', 'student__username', 'token__token')
    readonly_fields = ('submitted_at', 'ip_address')
    raw_id_fields = ('form', 'student', 'token')
    inlines = [FieldResponseInline]
    list_per_page = 20
    
    def get_responses_count(self, obj):
        return obj.responses.count()
    get_responses_count.short_description = 'Responses'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('form', 'student', 'token')

class FieldResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'field', 'get_value_preview', 'created_at')
    list_filter = ('field__field_type', 'created_at', 'field__form')
    search_fields = ('submission__form__title', 'field__label', 'value_text')
    readonly_fields = ('created_at', 'get_value_display')
    raw_id_fields = ('submission', 'field')
    list_per_page = 20
    
    def get_value_preview(self, obj):
        value = obj.get_value()
        if value:
            value_str = str(value)
            return value_str[:50] + "..." if len(value_str) > 50 else value_str
        return "No value"
    get_value_preview.short_description = 'Value Preview'
    
    def get_value_display(self, obj):
        return obj.get_value() or "No value"
    get_value_display.short_description = 'Value'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('submission', 'field', 'submission__form', 'field__form')

# Custom Admin Site Configuration
admin.site.site_header = "ID Card Management System"
admin.site.site_title = "ID Card Management"
admin.site.index_title = "Administration Dashboard"

# Register all models with their custom admin classes
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Architecture, ArchitectureAdmin)
admin.site.register(Form, FormAdmin)
admin.site.register(FormField, FormFieldAdmin)
admin.site.register(FormToken, FormTokenAdmin)
admin.site.register(FormSubmission, FormSubmissionAdmin)
admin.site.register(FieldResponse, FieldResponseAdmin)

# Optional: You can also add FormField as inline to Form admin
class FormAdminWithFields(FormAdmin):
    inlines = [FormFieldInline]

# Re-register Form with inlines
admin.site.unregister(Form)
admin.site.register(Form, FormAdminWithFields)