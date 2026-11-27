from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from core.auth_views import AuthTokenView, SessionTokenRefreshView
from core.views import inicio

urlpatterns = [
    path('', inicio, name='inicio'),
    path('admin/', admin.site.urls),
    path(
        'api/token/',
        AuthTokenView.as_view(),
        name='token_obtain_pair',
    ),
    path(
        'api/token/refresh/',
        SessionTokenRefreshView.as_view(),
        name='token_refresh',
    ),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    path('api/', include('core.urls')),
    re_path(r'^(?!api/|admin/|static/).*$', inicio, name='spa_fallback'),
]
