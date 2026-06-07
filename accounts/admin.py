from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.forms import MultipleChoiceField, CheckboxSelectMultiple, ModelForm
from .models import Profile, College, Department


class ProfileAdminForm(ModelForm):
    allowed_roles = MultipleChoiceField(
        choices=Profile.ROLE_CHOICES,
        widget=CheckboxSelectMultiple,
        label='الصلاحيات المسموحة لهذا الحساب',
        required=False,
    )

    class Meta:
        model = Profile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-fill the multiple choice field from the JSONField
            self.fields['allowed_roles'].initial = self.instance.allowed_roles

    def save(self, commit=True):
        profile = super().save(commit=False)
        # Save the list from multiple choice field back to JSON field
        profile.allowed_roles = self.cleaned_data['allowed_roles']
        if commit:
            profile.save()
        return profile

class ProfileInline(admin.StackedInline):
    model = Profile
    form = ProfileAdminForm
    can_delete = False
    verbose_name_plural = 'الملف الشخصي'
    fields = ['role', 'allowed_roles', 'college', 'academic_department', 'student_id', 'level', 'phone', 'is_active_account']


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'first_name', 'last_name', 'email', 'get_role', 'get_college', 'get_dept')

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except:
            return '-'
    get_role.short_description = 'الدور'

    def get_college(self, obj):
        try:
            return obj.profile.get_college_name()
        except:
            return '-'
    get_college.short_description = 'الكلية'

    def get_dept(self, obj):
        try:
            return obj.profile.get_department_name()
        except:
            return '-'
    get_dept.short_description = 'القسم'


class ProfileAdmin(admin.ModelAdmin):
    form = ProfileAdminForm
    list_display = ['user', 'role', 'display_allowed_roles', 'college', 'academic_department', 'student_id', 'level', 'is_active_account']
    list_filter = ['role', 'college', 'academic_department', 'level', 'is_active_account', 'created_by_admin']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'student_id']

    def display_allowed_roles(self, obj):
        return ", ".join(obj.get_allowed_roles_display())
    display_allowed_roles.short_description = 'الصلاحيات المسموحة'


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ['name', 'code']


class CollegeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'get_departments_count', 'get_students_count', 'get_instructors_count']
    search_fields = ['name', 'code']
    inlines = [DepartmentInline]


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'college', 'get_students_count', 'get_courses_count']
    list_filter = ['college']
    search_fields = ['name', 'code']


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(College, CollegeAdmin)
admin.site.register(Department, DepartmentAdmin)

admin.site.site_header = 'نظام الاختبارات الجامعي'
admin.site.site_title = 'نظام الاختبارات'
admin.site.index_title = 'لوحة الإدارة'
