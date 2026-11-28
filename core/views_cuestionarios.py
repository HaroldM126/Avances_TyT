from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cuestionario, Matricula
from .permissions import (
    PuedeConfigurarCuestionarios,
    PuedeConsultarCuestionarios,
    has_active_permission,
)
from .serializers_cuestionarios import (
    CuestionarioEstudianteSerializer,
    CuestionarioListSerializer,
    CuestionarioSerializer,
)
from .serializers_intentos import (
    IniciarIntentoCuestionarioInputSerializer,
    IniciarIntentoOutputSerializer,
)
from .services.intentos import iniciar_intento_para_usuario


def _simulacros_disponibles_estudiante(user):
    ahora = timezone.now()
    qs = Cuestionario.objects.filter(
        activo=True,
        estado=Cuestionario.ESTADO_PUBLICADO,
        fecha_apertura__lte=ahora,
        fecha_cierre__gte=ahora,
    ).select_related('curso__periodo')
    cursos = Matricula.objects.filter(
        estudiante=user,
        activa=True,
    ).values('curso_id')
    return qs.filter(Q(curso__isnull=True) | Q(curso_id__in=cursos))


@extend_schema_view(
    list=extend_schema(
        tags=['Simulacros'],
        summary='Listar cuestionarios configurados',
        parameters=[
            OpenApiParameter(
                name='activo',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filtrar por estado activo (true/false).',
            ),
        ],
    ),
    retrieve=extend_schema(tags=['Simulacros'], summary='Consultar detalle de cuestionario'),
    create=extend_schema(tags=['Simulacros'], summary='Crear cuestionario'),
    partial_update=extend_schema(tags=['Simulacros'], summary='Actualizar cuestionario'),
)
class CuestionarioViewSet(viewsets.ModelViewSet):
    queryset = Cuestionario.objects.all().order_by('-fecha_apertura', 'id')
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('disponibles', 'iniciar'):
            return [IsAuthenticated()]
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), PuedeConsultarCuestionarios()]
        return [IsAuthenticated(), PuedeConfigurarCuestionarios()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CuestionarioListSerializer
        if self.action == 'disponibles':
            return CuestionarioEstudianteSerializer
        return CuestionarioSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(creador=self.request.user)
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

    @extend_schema(
        tags=['Simulacros'],
        summary='Activar y publicar cuestionario',
        request=None,
        responses={200: CuestionarioSerializer, 400: OpenApiResponse(description='Datos o preguntas inválidas')},
    )
    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        cuestionario = self.get_object()
        if not cuestionario.fecha_apertura or not cuestionario.fecha_cierre:
            return Response(
                {'detail': 'Configura las fechas de apertura y cierre antes de publicar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cuestionario.full_clean()
        except ValidationError as error:
            return Response(
                {'detail': 'Hay datos inválidos en el cuestionario.', 'errores': getattr(error, 'message_dict', {})},
                status=status.HTTP_400_BAD_REQUEST,
            )
        errores = cuestionario.validar_preguntas()
        if errores:
            return Response(
                {'detail': 'No puedes activar el cuestionario.', 'errores': errores},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cuestionario.activo = True
        cuestionario.estado = Cuestionario.ESTADO_PUBLICADO
        cuestionario.save(update_fields=['activo', 'estado'])
        return Response(CuestionarioSerializer(cuestionario).data)

    @extend_schema(
        tags=['Simulacros'],
        summary='Desactivar cuestionario',
        request=None,
        responses={200: CuestionarioSerializer},
    )
    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        cuestionario = self.get_object()
        cuestionario.activo = False
        cuestionario.save(update_fields=['activo'])
        return Response(CuestionarioSerializer(cuestionario).data)

    @extend_schema(
        tags=['Simulacros'],
        summary='Listar simulacros disponibles para estudiante',
        responses={
            200: CuestionarioEstudianteSerializer(many=True),
            401: OpenApiResponse(description='No autenticado'),
            403: OpenApiResponse(description='Solo disponible para cuentas de estudiante'),
        },
    )
    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        if not request.user.groups.filter(name='Estudiante', rol__activo=True).exists():
            return Response(
                {'detail': 'Este listado está disponible para cuentas de estudiante.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = _simulacros_disponibles_estudiante(request.user)
        serializer = CuestionarioEstudianteSerializer(
            qs,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)

    @extend_schema(
        tags=['Simulacros'],
        summary='Iniciar un intento de evaluación',
        request=IniciarIntentoCuestionarioInputSerializer,
        responses={
            201: IniciarIntentoOutputSerializer,
            400: OpenApiResponse(description='El cuestionario no puede iniciarse'),
            403: OpenApiResponse(description='Sin permiso o contraseña incorrecta'),
            404: OpenApiResponse(description='Cuestionario no encontrado'),
        },
    )
    @action(detail=True, methods=['post'], url_path='iniciar')
    def iniciar(self, request, pk=None):
        payload, code = iniciar_intento_para_usuario(
            pk,
            request.user,
            request.data.get('contrasena', ''),
        )
        return Response(payload, status=code)


class SimulacroListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=['Simulacros'],
        summary='Listar simulacros disponibles',
        description=(
            'Para estudiantes devuelve los simulacros publicados y vigentes según sus matrículas. '
            'Para docentes/administradores autorizados devuelve los cuestionarios configurados.'
        ),
        parameters=[
            OpenApiParameter(
                name='activo',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filtrar por estado activo (solo para perfiles administrativos/docentes).',
            ),
        ],
        responses={
            200: CuestionarioEstudianteSerializer(many=True),
            401: OpenApiResponse(description='No autenticado'),
            403: OpenApiResponse(description='Sin rol o permiso para consultar simulacros'),
        },
    )
    def get(self, request):
        es_gestor = request.user.is_superuser or request.user.is_staff or any(
            has_active_permission(request.user, perm)
            for perm in ('configure_quizzes', 'manage_question_bank', 'view_results')
        )
        if es_gestor:
            qs = Cuestionario.objects.all().order_by('-fecha_apertura', 'id')
            if not (request.user.is_superuser or request.user.is_staff):
                qs = qs.filter(creador=request.user)
            activo = request.query_params.get('activo')
            if activo is not None:
                if activo.lower() in ('1', 'true', 'si', 'sí'):
                    qs = qs.filter(activo=True)
                elif activo.lower() in ('0', 'false', 'no'):
                    qs = qs.filter(activo=False)
            return Response(CuestionarioListSerializer(qs, many=True).data)

        if request.user.groups.filter(name='Estudiante', rol__activo=True).exists():
            qs = _simulacros_disponibles_estudiante(request.user)
            return Response(
                CuestionarioEstudianteSerializer(
                    qs,
                    many=True,
                    context={'request': request},
                ).data
            )

        return Response(
            {'detail': 'No tienes permiso para consultar simulacros.'},
            status=status.HTTP_403_FORBIDDEN,
        )
