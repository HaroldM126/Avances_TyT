from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .permissions import HasManageUsersPermission
from .serializers_usuarios import (
    DocenteRegistroSerializer,
    EstudianteRegistroSerializer,
)


class RegistroInstitucionalBaseView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, HasManageUsersPermission)


@extend_schema(tags=['Usuarios y Roles'], summary='Registrar estudiante con matrícula')
class RegistroEstudianteView(RegistroInstitucionalBaseView):
    serializer_class = EstudianteRegistroSerializer


@extend_schema(tags=['Usuarios y Roles'], summary='Registrar docente')
class RegistroDocenteView(RegistroInstitucionalBaseView):
    serializer_class = DocenteRegistroSerializer
