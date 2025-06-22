# worktracker/employees/admin.py

from django.contrib import admin
# Импортируем только те модели, которые реально существуют в вашем models.py
from .models import Project, Task, Employee, WorkLog, DailyWorkLog, Break

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project')
    list_filter = ('project',)
    search_fields = ('title',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'position', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position', 'department')
    list_filter = ('department', 'position')

@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'task', 'date', 'hours_spent')
    list_filter = ('date', 'employee', 'task__project')
    search_fields = ('employee__user__username', 'task__title')

@admin.register(DailyWorkLog)
class DailyWorkLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_time', 'end_time', 'total_worked_minutes')
    list_filter = ('employee', 'start_time')

@admin.register(Break)
class BreakAdmin(admin.ModelAdmin):
    list_display = ('work_log', 'break_type', 'start_time', 'end_time', 'duration_minutes')
    list_filter = ('break_type', 'work_log__employee')