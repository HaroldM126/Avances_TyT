from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


ROLE_ADMIN = 'Administrador'
ROLE_STUDENT = 'Estudiante'
ROLE_PERMISSION_CODENAMES = (
    'manage_users',
    'manage_roles',
    'manage_question_bank',
    'configure_quizzes',
    'view_results',
)


@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    if sender.name != 'core':
        return

    cuestionario = apps.get_model('core', 'Cuestionario')
    permissions = Permission.objects.filter(
        content_type__app_label='core',
        content_type__model=cuestionario._meta.model_name,
        codename__in=ROLE_PERMISSION_CODENAMES,
    )
    admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
    student_group, _ = Group.objects.get_or_create(name=ROLE_STUDENT)
    from .models import Rol
    Rol.objects.get_or_create(grupo=admin_group)
    Rol.objects.get_or_create(grupo=student_group)
    admin_group.permissions.set(permissions)
