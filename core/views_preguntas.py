from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Categoria, Competencia, Pregunta
from .permissions import PuedeGestionarPreguntas
from .serializers_preguntas import (
    CategoriaSerializer,
    CompetenciaSerializer,
    PreguntaListSerializer,
    PreguntaSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all().order_by('nombre')
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']


class CompetenciaViewSet(viewsets.ModelViewSet):
    queryset = Competencia.objects.all().order_by('nombre')
    serializer_class = CompetenciaSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']


class PreguntaViewSet(viewsets.ModelViewSet):
    queryset = Pregunta.objects.select_related('categoria', 'competencia').all()
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list':
            return PreguntaListSerializer
        return PreguntaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        categoria = params.get('categoria')
        competencia = params.get('competencia')
        tipo = params.get('tipo')
        activa = params.get('activa')
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        if competencia:
            qs = qs.filter(competencia_id=competencia)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if activa is not None:
            if activa.lower() in ('1', 'true', 'si', 'sí'):
                qs = qs.filter(activa=True)
            elif activa.lower() in ('0', 'false', 'no'):
                qs = qs.filter(activa=False)
        return qs

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Las preguntas no se borran: usa la acción "desactivar".'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        pregunta = self.get_object()
        pregunta.activa = False
        pregunta.save(update_fields=['activa'])
        return Response(
            PreguntaSerializer(pregunta).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        pregunta = self.get_object()
        pregunta.activa = True
        pregunta.save(update_fields=['activa'])
        return Response(
            PreguntaSerializer(pregunta).data,
            status=status.HTTP_200_OK,
        )