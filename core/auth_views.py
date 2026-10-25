from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from django.contrib.auth.models import Permission, User

from .permissions import HasManageRolesPermission, HasManageUsersPermission
from .models import Rol
from .serializers import (
    AuthTokenSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserSerializer,
)


class AuthTokenView(TokenObtainPairView):
    serializer_class = AuthTokenSerializer


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Debe enviar el refresh token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except (KeyError, ValueError, TokenError):
            return Response(
                {'detail': 'El refresh token no es válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.prefetch_related('groups').order_by('username')
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, HasManageUsersPermission)


class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.prefetch_related('groups')
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, HasManageUsersPermission)


class RoleListCreateView(generics.ListCreateAPIView):
    queryset = Rol.objects.select_related('grupo').prefetch_related(
        'grupo__permissions'
    )
    serializer_class = RoleSerializer
    permission_classes = (IsAuthenticated, HasManageRolesPermission)


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rol.objects.select_related('grupo').prefetch_related(
        'grupo__permissions'
    )
    serializer_class = RoleSerializer
    permission_classes = (IsAuthenticated, HasManageRolesPermission)


class PermissionListView(generics.ListAPIView):
    queryset = Permission.objects.filter(
        content_type__app_label='core',
        content_type__model='cuestionario',
    ).order_by('codename')
    serializer_class = PermissionSerializer
    permission_classes = (IsAuthenticated, HasManageRolesPermission)
