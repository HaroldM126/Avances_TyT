from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Cuestionario, CuestionarioPregunta, Intento, Pregunta, RespuestaIntento
from .permissions import PuedeConfigurarCuestionarios
from .serializers_cuestionarios import (
    CuestionarioEstudianteSerializer,
    CuestionarioListSerializer,
    CuestionarioSerializer,
)


class CuestionarioViewSet(viewsets.ModelViewSet):
    queryset = Cuestionario.objects.all().order_by('-fecha_apertura', 'id')
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('disponibles', 'iniciar'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), PuedeConfigurarCuestionarios()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CuestionarioListSerializer
        if self.action == 'disponibles':
            return CuestionarioEstudianteSerializer
        return CuestionarioSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        activo = params.get('activo')
        if activo is not None:
            if activo.lower() in ('1', 'true', 'si', 'sí'):
                qs = qs.filter(activo=True)
            elif activo.lower() in ('0', 'false', 'no'):
                qs = qs.filter(activo=False)
        return qs

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Los cuestionarios no se borran: usa la acción "desactivar".'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        cuestionario = self.get_object()
        errores = cuestionario.validar_preguntas()
        if errores:
            return Response(
                {'detail': 'No puedes activar el cuestionario.', 'errores': errores},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cuestionario.activo = True
        cuestionario.save(update_fields=['activo'])
        return Response(CuestionarioSerializer(cuestionario).data)

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        cuestionario = self.get_object()
        cuestionario.activo = False
        cuestionario.save(update_fields=['activo'])
        return Response(CuestionarioSerializer(cuestionario).data)

    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        qs = Cuestionario.objects.disponibles()
        serializer = CuestionarioEstudianteSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='iniciar')
    def iniciar(self, request, pk=None):
        cuestionario = self.get_object()
        puede, motivo = cuestionario.puede_iniciar(request.user)
        if not puede:
            return Response(
                {'detail': motivo},
                status=status.HTTP_400_BAD_REQUEST,
            )
        intento = Intento.objects.create(
            usuario=request.user,
            cuestionario=cuestionario,
        )
        RespuestaIntento.objects.bulk_create([
            RespuestaIntento(
                intento=intento,
                pregunta=relacion.pregunta,
            )
            for relacion in cuestionario.cuestionario_preguntas.select_related(
                'pregunta',
            )
        ])
        return Response(
            {
                'detail': 'Intento iniciado.',
                'intento_id': intento.id,
                'cuestionario_id': cuestionario.id,
                'duracion_minutos': cuestionario.duracion_minutos,
                'nota_maxima': str(cuestionario.nota_maxima),
            },
            status=status.HTTP_201_CREATED,
        )