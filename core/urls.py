from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .auth_views import (
    AuthTokenView,
    LogoutView,
    MeView,
    PermissionListView,
    RoleDetailView,
    RoleListCreateView,
    UserDetailView,
    UserListCreateView,
)
from .views_preguntas import (
    CategoriaViewSet,
    CompetenciaViewSet,
    PreguntaViewSet,
)

urlpatterns = [
    path('auth/token/', AuthTokenView.as_view(), name='auth_token'),
    path(
        'auth/token/refresh/',
        TokenRefreshView.as_view(),
        name='auth_token_refresh',
    ),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/me/', MeView.as_view(), name='auth_me'),
    path('users/', UserListCreateView.as_view(), name='user_list_create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('roles/', RoleListCreateView.as_view(), name='role_list_create'),
    path('roles/<int:pk>/', RoleDetailView.as_view(), name='role_detail'),
    path('permissions/', PermissionListView.as_view(), name='permission_list'),
]

router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('competencias', CompetenciaViewSet, basename='competencia')
router.register('preguntas', PreguntaViewSet, basename='pregunta')

urlpatterns += router.urls