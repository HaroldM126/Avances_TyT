from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Intento, RespuestaIntento
from .permissions import has_active_permission
from .serializers_intentos import (
    GuardarRespuestaInputSerializer,
    GuardarRespuestaOutputSerializer,
    IniciarIntentoInputSerializer,
    IniciarIntentoOutputSerializer,
    IntentoSerializer,
    ResultadoPermitidoSerializer,
    RevisionRespuestaSerializer,
)
from .services.intentos import iniciar_intento_para_usuario


def puede_ver_intento(usuario, intento):
    return (
        intento.usuario_id == usuario.id
        or usuario.is_superuser
        or has_active_permission(usuario, 'view_results')
    )


def _queryset_intentos_usuario(user):
    qs = Intento.objects.select_related(
        'cuestionario',
        'usuario',
        'curso',
        'periodo',
    ).prefetch_related(
        'respuestaintento_set__pregunta__opciones',
    )
    if user.is_superuser or user.is_staff:
        return qs
    if has_active_permission(user, 'view_results') or has_active_permission(user, 'ver_reportes'):
        return qs.filter(cuestionario__creador=user)
    if user.groups.filter(name='Estudiante', rol__activo=True).exists():
        return qs.filter(usuario=user)
    return None


@extend_schema_view(
    list=extend_schema(
        tags=['Intentos'],
        summary='Listar intentos permitidos',
        responses={
            200: IntentoSerializer(many=True),
            401: OpenApiResponse(description='No autenticado'),
        },
    ),
    create=extend_schema(
        tags=['Intentos'],
        summary='Registrar un intento',
        description=(
            'Inicia un nuevo intento para un simulacro disponible validando rol de estudiante, '
            'fechas de apertura/cierre, matrícula, límite de intentos y contraseña opcional.'
        ),
        request=IniciarIntentoInputSerializer,
        responses={
            201: IniciarIntentoOutputSerializer,
            400: OpenApiResponse(description='Datos inválidos o simulacro no disponible'),
            401: OpenApiResponse(description='No autenticado'),
            403: OpenApiResponse(description='Usuario sin rol estudiante o contraseña incorrecta'),
            404: OpenApiResponse(description='Simulacro no encontrado'),
        },
    ),
    retrieve=extend_schema(
        tags=['Intentos'],
        summary='Consultar detalle de un intento',
        responses={
            200: IntentoSerializer,
            401: OpenApiResponse(description='No autenticado'),
            403: OpenApiResponse(description='Sin permiso para consultar este intento'),
            404: OpenApiResponse(description='Intento no encontrado'),
        },
    ),
)
class IntentoViewSet(
    mixins.CreateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    serializer_class = IntentoSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = Intento.objects.select_related(
            'cuestionario',
            'usuario',
        ).prefetch_related(
            'respuestaintento_set__pregunta__opciones',
        )
        if self.request.user.is_superuser or has_active_permission(
            self.request.user,
            'view_results',
        ):
            if self.request.user.is_superuser or self.request.user.is_staff:
                return qs
            return qs.filter(cuestionario__creador=self.request.user)
        return qs.filter(usuario=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = IniciarIntentoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, code = iniciar_intento_para_usuario(
            serializer.validated_data['cuestionario'],
            request.user,
            serializer.validated_data.get('contrasena', ''),
        )
        return Response(payload, status=code)

    def retrieve(self, request, *args, **kwargs):
        intento = self.get_object()
        self._cerrar_si_vencido(intento)
        if not puede_ver_intento(request.user, intento):
            return Response(
                {'detail': 'No tienes permiso para consultar este intento.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=['Intentos'],
        summary='Guardar o limpiar respuesta de un intento en curso',
        request=GuardarRespuestaInputSerializer,
        responses={
            200: GuardarRespuestaOutputSerializer,
            400: OpenApiResponse(description='Intento cerrado o pregunta/opción inválida'),
            403: OpenApiResponse(description='Solo puedes responder tus propios intentos'),
        },
    )
    @action(detail=True, methods=('patch',), url_path='respuestas')
    def respuestas(self, request, pk=None):
        intento = self.get_object()
        if intento.usuario_id != request.user.id:
            return Response(
                {'detail': 'Solo puedes responder tus propios intentos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if self._cerrar_si_vencido(intento):
            return Response(IntentoSerializer(intento).data)
        if intento.enviado:
            return Response(
                {'detail': 'El intento ya fue enviado y no admite cambios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if self._cerrar_si_vencido(intento):
            return Response(
                {'detail': 'El tiempo del intento ya terminó.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pregunta_id = request.data.get('pregunta')
        opcion_id = request.data.get('opcion')
        try:
            respuesta = intento.respuestaintento_set.get(
                pregunta_id=pregunta_id,
            )
        except RespuestaIntento.DoesNotExist:
            return Response(
                {'detail': 'La pregunta no pertenece a este intento.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if opcion_id is not None:
            if not respuesta.pregunta.opciones.filter(pk=opcion_id).exists():
                return Response(
                    {'detail': 'La opción no pertenece a la pregunta.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            respuesta.opcion_id = opcion_id
        else:
            respuesta.opcion = None
        marcar_revision = request.data.get('marcada_revision')
        if marcar_revision is not None:
            respuesta.marcada_revision = bool(marcar_revision)
        respuesta.save(update_fields=('opcion', 'marcada_revision'))
        return Response(
            {
                'detail': 'Respuesta guardada.',
                'pregunta': respuesta.pregunta_id,
                'opcion': respuesta.opcion_id,
            },
        )

    @extend_schema(
        tags=['Intentos'],
        summary='Finalizar y calificar un intento',
        request=None,
        responses={
            200: IntentoSerializer,
            403: OpenApiResponse(description='Solo puedes enviar tus propios intentos'),
        },
    )
    @action(detail=True, methods=('post',), url_path='enviar')
    def enviar(self, request, pk=None):
        intento = self.get_object()
        if intento.usuario_id != request.user.id:
            return Response(
                {'detail': 'Solo puedes enviar tus propios intentos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if intento.enviado:
            return Response(IntentoSerializer(intento).data)

        with transaction.atomic():
            intento.puntaje = intento.calcular_puntaje()
            intento.enviado = True
            intento.estado = Intento.ESTADO_ENVIADO
            intento.fecha_envio = timezone.now()
            intento.save(update_fields=('puntaje', 'enviado', 'estado', 'fecha_envio'))

        return Response(IntentoSerializer(intento).data)

    @extend_schema(
        tags=['Intentos'],
        summary='Consultar revisión de respuestas de un intento enviado',
        responses={
            200: RevisionRespuestaSerializer(many=True),
            400: OpenApiResponse(description='El intento todavía no ha sido enviado'),
            403: OpenApiResponse(description='Revisión o resultado no habilitado'),
        },
    )
    @action(detail=True, methods=('get',), url_path='revision')
    def revision(self, request, pk=None):
        intento = self.get_object()
        if not puede_ver_intento(request.user, intento):
            return Response(
                {'detail': 'No tienes permiso para consultar este intento.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        self._cerrar_si_vencido(intento)
        if not intento.enviado:
            return Response(
                {'detail': 'El intento todavía no ha sido enviado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not intento.cuestionario.permitir_revision and not (
            request.user.is_superuser
            or has_active_permission(request.user, 'view_results')
        ):
            return Response(
                {'detail': 'La revisión no está habilitada para este cuestionario.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if (
            intento.usuario_id == request.user.id
            and not intento.cuestionario.publicar_resultado
        ):
            return Response(
                {'detail': 'El resultado todavía no ha sido publicado.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        respuestas = intento.respuestaintento_set.select_related(
            'pregunta',
            'opcion',
        ).prefetch_related('pregunta__opciones')
        return Response(RevisionRespuestaSerializer(respuestas, many=True).data)

    def _cerrar_si_vencido(self, intento):
        if intento.enviado or not intento.esta_vencido():
            return False
        intento.puntaje = intento.calcular_puntaje()
        intento.enviado = True
        intento.estado = Intento.ESTADO_VENCIDO
        intento.fecha_envio = timezone.now()
        intento.save(update_fields=(
            'puntaje',
            'enviado',
            'estado',
            'fecha_envio',
        ))
        return True


class ResultadosPermitidosView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=['Resultados'],
        summary='Consultar resultados permitidos',
        description=(
            'Lista los resultados de intentos permitidos según el rol y permisos del usuario autenticado. '
            'Los estudiantes únicamente ven sus propios resultados (ocultando la nota si publicar_resultado=False).'
        ),
        parameters=[
            OpenApiParameter(
                name='cuestionario',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filtrar por ID de cuestionario/simulacro.',
            ),
            OpenApiParameter(
                name='estado',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=['EN_CURSO', 'ENVIADO', 'VENCIDO', 'ANULADO'],
                description='Filtrar por estado del intento.',
            ),
            OpenApiParameter(
                name='enviado',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filtrar por intentos enviados (true/false).',
            ),
        ],
        responses={
            200: ResultadoPermitidoSerializer(many=True),
            400: OpenApiResponse(description='Parámetro de filtro inválido'),
            401: OpenApiResponse(description='No autenticado'),
            403: OpenApiResponse(description='Sin permisos para consultar resultados'),
        },
    )
    def get(self, request):
        qs = _queryset_intentos_usuario(request.user)
        if qs is None:
            return Response(
                {'detail': 'No tienes permiso para consultar resultados.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        cuestionario_id = request.query_params.get('cuestionario')
        if cuestionario_id:
            try:
                qs = qs.filter(cuestionario_id=int(cuestionario_id))
            except (TypeError, ValueError):
                return Response(
                    {'cuestionario': 'Debe ser un identificador numérico válido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        estado = request.query_params.get('estado')
        if estado:
            valid_states = {choice[0] for choice in Intento.ESTADO_CHOICES}
            if estado not in valid_states:
                return Response(
                    {'estado': f'Estado inválido. Usa uno de: {", ".join(sorted(valid_states))}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(estado=estado)

        enviado = request.query_params.get('enviado')
        if enviado is not None:
            if enviado.lower() in ('1', 'true', 'si', 'sí'):
                qs = qs.filter(enviado=True)
            elif enviado.lower() in ('0', 'false', 'no'):
                qs = qs.filter(enviado=False)
            else:
                return Response(
                    {'enviado': 'Usa true o false.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = ResultadoPermitidoSerializer(
            qs,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)
