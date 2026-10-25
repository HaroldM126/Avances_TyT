from rest_framework.permissions import BasePermission


class HasManageUsersPermission(BasePermission):
    message = 'No tiene permiso para administrar usuarios.'

    def has_permission(self, request, view):
        return has_active_permission(request.user, 'manage_users')


class HasManageRolesPermission(BasePermission):
    message = 'No tiene permiso para administrar roles.'

    def has_permission(self, request, view):
        return has_active_permission(request.user, 'manage_roles')


def has_active_permission(user, codename):
    if user.is_superuser:
        return True
    return user.groups.filter(
        rol__activo=True,
        permissions__content_type__app_label='core',
        permissions__codename=codename,
    ).exists()
