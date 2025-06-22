from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ # Рекомендуется для verbose_name

# --- Добавлены недостающие модели для полноты контекста ---
# Модель WorkLog ссылается на 'Task', поэтому её необходимо определить.
# Я добавил минимальные версии Project и Task, чтобы код был рабочим.

class Project(models.Model):
    title = models.CharField(_("Название проекта"), max_length=200)

    class Meta:
        verbose_name = _("Проект")
        verbose_name_plural = _("Проекты")

    def __str__(self):
        return self.title

class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name=_("Проект"))
    title = models.CharField(_("Название задачи"), max_length=200)

    class Meta:
        verbose_name = _("Задача")
        verbose_name_plural = _("Задачи")

    def __str__(self):
        return self.title

# --- Исправления в ваших моделях ---

# Сотрудники
class Employee(models.Model):
    # Улучшение: добавлен related_name для удобных обратных запросов
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    position = models.CharField(_("Должность"), max_length=100)
    department = models.CharField(_("Отдел"), max_length=100)

    class Meta:
        verbose_name = _("Сотрудник")
        verbose_name_plural = _("Сотрудники")
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        # Улучшение: более надежный __str__, который работает, даже если имя не задано
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username


# Рабочие часы (задача → сотрудник → время)
class WorkLog(models.Model):
    # Улучшение: добавлен related_name
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='work_logs', verbose_name=_("Задача"))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='work_logs', verbose_name=_("Сотрудник"))
    # Критическая ошибка исправлена: default=timezone.now, а не timezone.now()
    date = models.DateField(_("Дата"), default=timezone.now)
    hours_spent = models.DecimalField(_("Часы"), max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = _("Запись о работе")
        verbose_name_plural = _("Записи о работе")
        ordering = ['-date', 'employee']

    def __str__(self):
        return f"{self.employee} - {self.task.title} ({self.hours_spent} ч)"


# Учёт рабочего времени (начало/окончание дня, перерывы)
class DailyWorkLog(models.Model):
    # Улучшение: добавлен related_name
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='daily_logs', verbose_name=_("Сотрудник"))
    start_time = models.DateTimeField(_("Время начала"), auto_now_add=True)
    end_time = models.DateTimeField(_("Время окончания"), null=True, blank=True)

    class Meta:
        verbose_name = _("Дневной отчёт")
        verbose_name_plural = _("Дневные отчёты")
        ordering = ['-start_time']

    # Улучшение: использование @property для вычисляемых полей
    @property
    def total_worked_minutes(self):
        if self.end_time and self.start_time:
            # Исправлено: убеждаемся, что start_time тоже есть
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return 0

    def __str__(self):
        # Улучшение: форматирование даты для большей читаемости
        return f"{self.employee} ({self.start_time.strftime('%d.%m.%Y')})"


# Перерывы (связаны с DailyWorkLog)
class Break(models.Model):
    # Улучшение: добавлен related_name
    work_log = models.ForeignKey(DailyWorkLog, on_delete=models.CASCADE, related_name='breaks', verbose_name=_("Рабочий день"))
    start_time = models.DateTimeField(_("Время начала"))
    # Логическая ошибка исправлена: end_time должно быть необязательным,
    # так как перерыв может быть еще не закончен
    end_time = models.DateTimeField(_("Время окончания"), null=True, blank=True)
    break_type = models.CharField(
        _("Тип перерыва"),
        max_length=50,
        choices=[
            ('lunch', _('Обед')),
            ('rest', _('Отдых')),
            ('meeting', _('Встреча'))
        ]
    )

    class Meta:
        verbose_name = _("Перерыв")
        verbose_name_plural = _("Перерывы")
        ordering = ['start_time']

    # Улучшение: использование @property
    @property
    def duration_minutes(self):
        # Критическая ошибка исправлена: добавлена проверка на None, чтобы избежать TypeError
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return 0 # Возвращаем 0, если перерыв не закончен

    def __str__(self):
        # Вызываем свойство, а не метод
        return f"{self.get_break_type_display()} ({self.duration_minutes} мин)"