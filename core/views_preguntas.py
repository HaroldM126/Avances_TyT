from django.db import transaction
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .excel_utils import construir_plantilla, guardar_filas, validar_excel
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


class PlantillaExcelView(APIView):
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]

    def get(self, request):
        buffer = construir_plantilla()
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="plantilla_preguntas.xlsx"'
        return response


class ImportarPreviewView(APIView):
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'detail': 'Debes adjuntar un archivo en el campo "archivo".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        resultado = validar_excel(archivo)
        if resultado['error_global']:
            return Response(
                {'detail': resultado['error_global']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filas = resultado['filas']
        validas = sum(1 for f in filas if f.valida)
        invalidas = len(filas) - validas
        payload = {
            'total': len(filas),
            'validas': validas,
            'invalidas': invalidas,
            'filas': [
                {
                    'numero': f.numero,
                    'valida': f.valida,
                    'errores': f.errores,
                    'datos': f.datos,
                }
                for f in filas
            ],
        }
        return Response(payload, status=status.HTTP_200_OK)


class ImportarConfirmarView(APIView):
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'detail': 'Debes adjuntar un archivo en el campo "archivo".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        resultado = validar_excel(archivo)
        if resultado['error_global']:
            return Response(
                {'detail': resultado['error_global']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filas = resultado['filas']
        invalidas = [f for f in filas if not f.valida]
        if invalidas:
            return Response(
                {
                    'detail': 'Hay filas invalidas: corrige el archivo antes de confirmar.',
                    'filas_invalidas': [
                        {'numero': f.numero, 'errores': f.errores}
                        for f in invalidas
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                creadas = guardar_filas(filas)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {'detail': f'{creadas} preguntas importadas correctamente.'},
            status=status.HTTP_201_CREATED,
        )