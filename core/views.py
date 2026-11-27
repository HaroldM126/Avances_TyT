from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def inicio(request, resource=None):
    index_file = settings.FRONTEND_DIST_DIR / 'index.html'
    if index_file.exists():
        return HttpResponse(
            index_file.read_text(encoding='utf-8'),
            content_type='text/html; charset=utf-8',
        )
    return HttpResponse('✅ Simulador TyT funcionando correctamente')


class HealthCheckView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        tags=['Sistema'],
        summary='Verificar estado de la aplicación y conexión a base de datos',
        description=(
            'Ejecuta una consulta SELECT 1 sobre la base de datos configurada '
            '(MariaDB/MySQL en producción) sin exponer credenciales.'
        ),
        responses={
            200: inline_serializer(
                name='HealthCheckOk',
                fields={
                    'status': serializers.CharField(),
                    'database': serializers.CharField(),
                    'engine': serializers.CharField(),
                },
            ),
            503: OpenApiResponse(description='Error de conexión a la base de datos'),
        },
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            return Response(
                {
                    'status': 'ok',
                    'database': 'ok',
                    'engine': connection.vendor,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {
                    'status': 'error',
                    'database': 'unavailable',
                    'engine': connection.vendor,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
