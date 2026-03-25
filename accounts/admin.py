from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'الملف الشخصي'


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'first_name', 'last_name', 'email', 'get_role')

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except:
            return '-'
    get_role.short_description = 'الدور'


from .models import Profile, College, Department


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'academic_department', 'student_id']
    list_filter = ['role', 'academic_department']


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(College)
admin.site.register(Department)

admin.site.site_header = 'نظام الاختبارات الجامعي'
admin.site.site_title = 'نظام الاختبارات'
admin.site.index_title = 'لوحة الإدارة'
