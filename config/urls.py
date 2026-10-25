from django.contrib import admin
from django.urls import include, path
from core.views import inicio
from core.auth_views import AuthTokenView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('', inicio),

    path('admin/', admin.site.urls),

    path(
        'api/token/',
        AuthTokenView.as_view(),
        name='token_obtain_pair'
    ),

    path(
        'api/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),
    path('api/', include('core.urls')),
]