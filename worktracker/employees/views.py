# --- 1. Очистка и исправление импортов ---
import json
from collections import defaultdict

from django.db.models import Count, Sum, F, ExpressionWrapper, fields
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST # Улучшение: для безопасности
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test

# Импортируем модели один раз и только те, что нужны
from .models import Employee, Project, Task, TaskTime, DailyWorkLog, Break
# from .models import WorkLog # <- Удален, так как не используется в исправленной версии


# --- 2. Представления для календаря и задач ---

class CalendarView(TemplateView):
    template_name = 'calendar.html'
    # Улучшение: передаем в контекст только то, что нужно шаблону.
    # Данные для календаря лучше загружать асинхронно через API.

def calendar_events(request):
    # Критическая ошибка (предположение): Модель Task, скорее всего, не имеет полей start_date и end_date.
    # В вашем admin.py для Task указан due_date. Этот код будет работать,
    # только если в модели Task есть эти поля. Если их нет, код вызовет AttributeError.
    # Для примера, я оставляю логику, но в реальном проекте это нужно проверить.
    try:
        tasks = Task.objects.all()
        events = []
        for task in tasks:
            # Проверяем наличие полей, чтобы избежать ошибок
            if hasattr(task, 'start_date') and hasattr(task, 'end_date') and task.start_date and task.end_date:
                events.append({
                    'id': task.id,
                    'title': task.title,
                    'start': task.start_date.isoformat(),
                    'end': task.end_date.isoformat(),
                    'is_in_progress': task.is_in_progress
                })
        return JsonResponse(events, safe=False)
    except AttributeError as e:
        return JsonResponse({'error': f'Модель Task не содержит необходимых полей (start_date/end_date). {e}'}, status=500)

# Улучшение: Ограничиваем метод только POST-запросами
@csrf_exempt
@require_POST
def update_task_date(request, task_id):
    # Исправление: Используем get_object_or_404 для обработки несуществующих задач
    task = get_object_or_404(Task, id=task_id)
    try:
        data = json.loads(request.body)
        # Улучшение: Используем .get() для безопасного доступа к ключам
        start_date = data.get('start')
        end_date = data.get('end')
        if not start_date or not end_date:
            return HttpResponseBadRequest("Отсутствуют 'start' или 'end' в теле запроса.")

        task.start_date = start_date
        task.end_date = end_date
        task.save(update_fields=['start_date', 'end_date']) # Улучшение: обновляем только нужные поля
        return JsonResponse({'status': 'success'})
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Неверный формат JSON.")

# --- 3. Представления для отслеживания времени по задачам (TaskTime) ---

@csrf_exempt
@require_POST
def start_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    # Исправление: Проверяем, нет ли уже запущенной задачи для этого пользователя
    existing_task_time = TaskTime.objects.filter(task=task, user=request.user, end_time__isnull=True).exists()
    if existing_task_time:
        return JsonResponse({'status': 'error', 'message': 'Эта задача уже запущена.'}, status=400)

    TaskTime.objects.create(task=task, user=request.user)
    return JsonResponse({'status': 'started'})


@csrf_exempt
@require_POST
def end_task(request, task_id):
    # Исправление: Используем get_object_or_404 в блоке try-except для более точной обработки ошибок
    try:
        task_time = TaskTime.objects.get(task_id=task_id, user=request.user, end_time__isnull=True)
        task_time.end_time = timezone.now()
        task_time.save(update_fields=['end_time'])
        return JsonResponse({'status': 'ended'})
    except TaskTime.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Нет активной сессии для этой задачи.'}, status=404)


def task_time_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Улучшение: Оптимизированный запрос к БД с помощью аннотаций
    query = TaskTime.objects.filter(end_time__isnull=False)

    if start_date:
        query = query.filter(start_time__date__gte=start_date)
    if end_date:
        query = query.filter(end_time__date__lte=end_date)

    duration_expression = ExpressionWrapper(F('end_time') - F('start_time'), output_field=fields.DurationField())

    time_data = query.values('user__username').annotate(
        total_duration=Sum(duration_expression)
    ).order_by('user__username')

    labels = [item['user__username'] for item in time_data]
    # Данные в минутах
    data = [round(item['total_duration'].total_seconds() / 60) for item in time_data]

    return render(request, 'time_report.html', {
        'labels': json.dumps(labels),
        'data': json.dumps(data)
    })

# --- 4. Представления для ежедневного учета рабочего времени (DailyWorkLog) ---

@csrf_exempt
@require_POST
def start_day(request):
    # Исправление: Проверяем, что у пользователя есть профиль Employee
    try:
        employee = request.user.employee_profile # Предполагается related_name='employee_profile'
    except Employee.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Профиль сотрудника не найден.'}, status=404)

    # Исправление: Проверяем, не начат ли уже день
    if DailyWorkLog.objects.filter(employee=employee, end_time__isnull=True).exists():
        return JsonResponse({'status': 'error', 'message': 'Рабочий день уже начат.'}, status=400)

    log = DailyWorkLog.objects.create(employee=employee)
    return JsonResponse({'status': 'started', 'work_log_id': log.id})


@csrf_exempt
@require_POST
def end_day(request):
    try:
        # Улучшение: Ищем активный лог для текущего пользователя, а не по ID
        work_log = DailyWorkLog.objects.get(employee__user=request.user, end_time__isnull=True)
        work_log.end_time = timezone.now()
        work_log.save(update_fields=['end_time'])
        return JsonResponse({'status': 'ended'})
    except DailyWorkLog.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Активный рабочий день не найден.'}, status=404)


@csrf_exempt
@require_POST
def add_break(request):
    try:
        # Ищем активный рабочий день для сотрудника
        work_log = DailyWorkLog.objects.get(employee__user=request.user, end_time__isnull=True)
        data = json.loads(request.body)
        
        # Улучшение: Проверяем, что все данные пришли
        start_time = data.get('start')
        end_time = data.get('end')
        break_type = data.get('type')
        
        if not all([start_time, end_time, break_type]):
            return HttpResponseBadRequest("Отсутствуют необходимые данные для создания перерыва.")

        Break.objects.create(
            work_log=work_log,
            start_time=start_time,
            end_time=end_time,
            break_type=break_type
        )
        return JsonResponse({'status': 'break_added'})
    except DailyWorkLog.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Активный рабочий день не найден.'}, status=404)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Неверный формат JSON.")

# --- 5. Представления для отчетов и админки ---

def daily_work_report(request):
    # Улучшение: Решаем проблему N+1 запроса с помощью prefetch_related
    work_logs = DailyWorkLog.objects.select_related('employee__user').prefetch_related('breaks').all()
    data = []

    for log in work_logs:
        total_time = log.total_worked_minutes # Используем свойство, а не метод

        # Исправление: Безопасный подсчет времени перерывов, учитывая что end_time может быть None
        break_time = sum(
            b.duration_minutes for b in log.breaks.all() if b.end_time
        )
        net_time = total_time - break_time

        data.append({
            'employee': log.employee.user.username,
            'total_minutes': total_time,
            'breaks_minutes': break_time,
            'net_minutes': net_time
        })
    return JsonResponse(data, safe=False)


# Улучшение: Декоратор для проверки прав суперпользователя
def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superuser)
def admin_dashboard(request):
    projects_count = Project.objects.count()
    tasks_in_progress_count = Task.objects.filter(is_in_progress=True).count()
    active_employees_count = DailyWorkLog.objects.filter(end_time__isnull=True).count()

    # Улучшение: Передаем в шаблон только агрегированные данные, а не все объекты
    context = {
        'projects_count': projects_count,
        'tasks_in_progress_count': tasks_in_progress_count,
        'active_employees_count': active_employees_count,
    }
    return render(request, 'admin_dashboard.html', context)