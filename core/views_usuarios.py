from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .permissions import HasManageUsersPermission
from .serializers_usuarios import (
    DocenteRegistroSerializer,
    EstudianteRegistroSerializer,
)


class RegistroInstitucionalBaseView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, HasManageUsersPermission)


class RegistroEstudianteView(RegistroInstitucionalBaseView):
    serializer_class = EstudianteRegistroSerializer


class RegistroDocenteView(RegistroInstitucionalBaseView):
    serializer_class = DocenteRegistroSerializer
