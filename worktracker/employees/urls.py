from django.urls import include, path
from . import views
from .views import update_task_date

urlpatterns = [
    # Календарь и задачи
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('task/<int:task_id>/update-date/', update_task_date, name='update_task_date'),
    path('task/<int:task_id>/start/', views.start_task),
    path('task/<int:task_id>/end/', views.end_task),
    path('task-report/<int:employee_id>/', views.task_time_report),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employees/', include('employees.urls')),

    # Учёт рабочего времени (новые маршруты)
    path('start-day/', views.start_day),
    path('end-day/<int:work_log_id>/', views.end_day),
    path('add-break/<int:work_log_id>/', views.add_break),
    path('daily-report/', views.daily_work_report),
]