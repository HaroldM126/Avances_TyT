from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Intento, Pregunta, RespuestaIntento
from .permissions import has_active_permission
from .serializers_intentos import (
    IntentoSerializer,
    RevisionRespuestaSerializer,
)


def puede_ver_intento(usuario, intento):
    return (
        intento.usuario_id == usuario.id
        or usuario.is_superuser
        or has_active_permission(usuario, 'view_results')
    )


class IntentoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IntentoSerializer
    permission_classes = (IsAuthenticated,)

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
            return qs
        return qs.filter(usuario=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        intento = self.get_object()
        self._cerrar_si_vencido(intento)
        if not puede_ver_intento(request.user, intento):
            return Response(
                {'detail': 'No tienes permiso para consultar este intento.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

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
        respuesta.save(update_fields=('opcion',))
        return Response(
            {
                'detail': 'Respuesta guardada.',
                'pregunta': respuesta.pregunta_id,
                'opcion': respuesta.opcion_id,
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
            intento.save(update_fields=('puntaje', 'enviado', 'fecha_envio'))

        return Response(IntentoSerializer(intento).data)

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
