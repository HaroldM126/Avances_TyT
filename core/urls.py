from django.urls import path
from rest_framework.routers import DefaultRouter
from .auth_views import (
    AuthTokenView,
    LogoutView,
    MeView,
    PermissionListView,
    RoleDetailView,
    RoleListCreateView,
    SessionTokenRefreshView,
    UserDetailView,
    UserListCreateView,
)
from .views_cuestionarios import CuestionarioViewSet
from .views_preguntas import (
    CategoriaViewSet,
    CompetenciaViewSet,
    ImportarConfirmarView,
    ImportacionDetailView,
    ImportacionListView,
    ImportarPreviewView,
    PlantillaExcelView,
    PreguntaViewSet,
)
from .views_intentos import IntentoViewSet
from .views_reportes import (
    ConsultaReporteView,
    CursosAcademicosView,
    ExportarReporteView,
    FiltrosReporteView,
    HistorialEstudianteView,
)

urlpatterns = [
    path('auth/token/', AuthTokenView.as_view(), name='auth_token'),
    path(
        'auth/token/refresh/',
        SessionTokenRefreshView.as_view(),
        name='auth_token_refresh',
    ),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/me/', MeView.as_view(), name='auth_me'),
    path('users/', UserListCreateView.as_view(), name='user_list_create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('roles/', RoleListCreateView.as_view(), name='role_list_create'),
    path('roles/<int:pk>/', RoleDetailView.as_view(), name='role_detail'),
    path('permissions/', PermissionListView.as_view(), name='permission_list'),

    path(
        'preguntas/importar/plantilla/',
        PlantillaExcelView.as_view(),
        name='preguntas_importar_plantilla',
    ),
    path(
        'preguntas/importar/preview/',
        ImportarPreviewView.as_view(),
        name='preguntas_importar_preview',
    ),
    path(
        'preguntas/importar/confirmar/',
        ImportarConfirmarView.as_view(),
        name='preguntas_importar_confirmar',
    ),
    path(
        'preguntas/importar/',
        ImportacionListView.as_view(),
        name='preguntas_importar_list',
    ),
    path(
        'preguntas/importar/<int:pk>/',
        ImportacionDetailView.as_view(),
        name='preguntas_importar_detail',
    ),
    path('reportes/filtros/', FiltrosReporteView.as_view(), name='reportes_filtros'),
    path(
        'cursos-academicos/',
        CursosAcademicosView.as_view(),
        name='cursos_academicos',
    ),
    path('reportes/consultas/', ConsultaReporteView.as_view(), name='reportes_consultas'),
    path(
        'reportes/historial/<int:estudiante_id>/',
        HistorialEstudianteView.as_view(),
        name='reportes_historial',
    ),
    path(
        'reportes/exportar/<str:tipo>/',
        ExportarReporteView.as_view(),
        name='reportes_exportar',
    ),
    path('reportes/', ConsultaReporteView.as_view(), name='reportes'),
]

router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('competencias', CompetenciaViewSet, basename='competencia')
router.register('preguntas', PreguntaViewSet, basename='pregunta')
router.register('cuestionarios', CuestionarioViewSet, basename='cuestionario')
router.register('intentos', IntentoViewSet, basename='intento')

urlpatterns += router.urls