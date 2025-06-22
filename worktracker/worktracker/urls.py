# --- 1. Исправлены и очищены импорты ---
from django.urls import include, path
from . import views  # Используем один последовательный импорт для всех представлений

# Этот файл, скорее всего, является urls.py приложения 'employees',
# поэтому мы используем относительный импорт (from . import views).

urlpatterns = [
    # Календарь и задачи
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('task/<int:task_id>/update-date/', views.update_task_date, name='update_task_date'),
    
    # --- 2. Добавлены имена (name) для всех маршрутов ---
    path('task/<int:task_id>/start/', views.start_task, name='start_task'),
    path('task/<int:task_id>/end/', views.end_task, name='end_task'),
    
    # --- 3. Исправлены логические несоответствия с views.py ---
    # Представление task_time_report не принимает employee_id, оно показывает общий отчет.
    path('task-report/', views.task_time_report, name='task_time_report'),
    path('employees/', include('employees.urls')),

    
    # Учёт рабочего времени
    path('start-day/', views.start_day, name='start_day'),
    
    # Представления end_day и add_break больше не принимают work_log_id в URL.
    # Они автоматически находят активный рабочий день для текущего пользователя.
    path('end-day/', views.end_day, name='end_day'),
    path('add-break/', views.add_break, name='add_break'),
    
    path('daily-report/', views.daily_work_report, name='daily_work_report'),

    # Админ-панель (если это кастомная панель, а не стандартный /admin/)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]