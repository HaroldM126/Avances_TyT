"""Lógica de negocio compartida para iniciar intentos de evaluación."""

from django.db import transaction
from rest_framework import status

from core.models import Cuestionario, Intento, RespuestaIntento


def iniciar_intento_para_usuario(cuestionario_id, user, contrasena=''):
    """Valida reglas del simulacro e inicia un intento con sus respuestas base."""
    if not user.groups.filter(name='Estudiante', rol__activo=True).exists():
        return (
            {'detail': 'Solo una cuenta de estudiante puede iniciar una evaluación.'},
            status.HTTP_403_FORBIDDEN,
        )
    with transaction.atomic():
        cuestionario = (
            Cuestionario.objects.select_for_update()
            .filter(pk=cuestionario_id)
            .first()
        )
        if cuestionario is None:
            return (
                {'detail': 'El simulacro o cuestionario no existe.'},
                status.HTTP_404_NOT_FOUND,
            )
        puede, motivo = cuestionario.puede_iniciar(user)
        if not puede:
            return {'detail': motivo}, status.HTTP_400_BAD_REQUEST
        if not cuestionario.validar_contrasena(contrasena):
            return (
                {'detail': 'La contraseña de acceso no es correcta.'},
                status.HTTP_403_FORBIDDEN,
            )
        intento = Intento.objects.create(
            usuario=user,
            cuestionario=cuestionario,
            curso=cuestionario.curso,
            periodo=cuestionario.curso.periodo if cuestionario.curso_id else None,
        )
    RespuestaIntento.objects.bulk_create([
        RespuestaIntento(
            intento=intento,
            pregunta=relacion.pregunta,
        )
        for relacion in cuestionario.cuestionario_preguntas.select_related('pregunta')
    ])
    return (
        {
            'detail': 'Intento iniciado.',
            'intento_id': intento.id,
            'cuestionario_id': cuestionario.id,
            'duracion_minutos': cuestionario.duracion_minutos,
            'nota_maxima': str(cuestionario.nota_maxima),
        },
        status.HTTP_201_CREATED,
    )
