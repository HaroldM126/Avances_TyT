import hashlib
import io

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .excel_utils import (
    COLUMNAS_ESPERADAS,
    FilaValidada,
    construir_plantilla,
    guardar_filas,
    validar_excel,
)
from openpyxl import Workbook
from .models import (
    Categoria,
    Competencia,
    FilaImportacionPregunta,
    ImportacionPreguntas,
    Pregunta,
)
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


class ImportacionListView(APIView):
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]

    def get(self, request):
        importaciones = ImportacionPreguntas.objects.filter(
            usuario=request.user,
        )
        return Response([
            {
                'id': item.id,
                'archivo_nombre': item.archivo_nombre,
                'estado': item.estado,
                'total': item.total,
                'validas': item.validas,
                'invalidas': item.invalidas,
                'preguntas_creadas': item.preguntas_creadas,
                'error_global': item.error_global,
                'creado_en': item.creado_en,
                'confirmado_en': item.confirmado_en,
            }
            for item in importaciones
        ])


class ImportacionDetailView(APIView):
    permission_classes = [IsAuthenticated, PuedeGestionarPreguntas]

    def get(self, request, pk):
        try:
            importacion = ImportacionPreguntas.objects.prefetch_related(
                'filas',
            ).get(pk=pk, usuario=request.user)
        except ImportacionPreguntas.DoesNotExist:
            return Response(
                {'detail': 'La importación no existe o no te pertenece.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            'id': importacion.id,
            'archivo_nombre': importacion.archivo_nombre,
            'estado': importacion.estado,
            'total': importacion.total,
            'validas': importacion.validas,
            'invalidas': importacion.invalidas,
            'preguntas_creadas': importacion.preguntas_creadas,
            'error_global': importacion.error_global,
            'filas': [
                {
                    'numero': fila.numero,
                    'valida': fila.valida,
                    'errores': fila.errores,
                    'datos': fila.datos,
                }
                for fila in importacion.filas.all()
            ],
        })

    def patch(self, request, pk):
        try:
            importacion = ImportacionPreguntas.objects.get(
                pk=pk,
                usuario=request.user,
            )
        except ImportacionPreguntas.DoesNotExist:
            return Response(
                {'detail': 'La importación no existe o no te pertenece.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        filas = request.data.get('filas')
        if not isinstance(filas, list) or not filas:
            return Response(
                {'detail': 'Debes enviar al menos una fila para validar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(COLUMNAS_ESPERADAS)
        for fila in filas:
            datos = fila.get('datos', {})
            opciones = {
                item.get('letra'): item.get('texto', '')
                for item in datos.get('opciones', [])
            }
            sheet.append([
                datos.get('categoria', ''),
                datos.get('competencia', ''),
                datos.get('tipo', ''),
                datos.get('texto_base', ''),
                datos.get('enunciado', ''),
                datos.get('retroalimentacion', ''),
                datos.get('explicacion', ''),
                datos.get('puntaje', ''),
                opciones.get('A', ''),
                opciones.get('B', ''),
                opciones.get('C', ''),
                opciones.get('D', ''),
                ','.join(datos.get('correctas', [])),
            ])
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        resultado = validar_excel(buffer)
        filas_validadas = resultado['filas']
        importacion.filas.all().delete()
        FilaImportacionPregunta.objects.bulk_create([
            FilaImportacionPregunta(
                importacion=importacion,
                numero=fila.numero,
                valida=fila.valida,
                errores=fila.errores,
                datos=fila.datos,
            )
            for fila in filas_validadas
        ])
        validas = sum(fila.valida for fila in filas_validadas)
        importacion.total = len(filas_validadas)
        importacion.validas = validas
        importacion.invalidas = len(filas_validadas) - validas
        importacion.estado = (
            ImportacionPreguntas.ESTADO_PREVIA
            if importacion.invalidas == 0
            else ImportacionPreguntas.ESTADO_ERROR
        )
        importacion.error_global = resultado['error_global'] or ''
        importacion.save(update_fields=(
            'total', 'validas', 'invalidas', 'estado', 'error_global',
        ))
        return Response({
            'importacion_id': importacion.id,
            'total': importacion.total,
            'validas': importacion.validas,
            'invalidas': importacion.invalidas,
            'filas': [
                {
                    'numero': fila.numero,
                    'valida': fila.valida,
                    'errores': fila.errores,
                    'datos': fila.datos,
                }
                for fila in filas_validadas
            ],
        })


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
        contenido = archivo.read()
        archivo.seek(0)
        archivo_hash = hashlib.sha256(contenido).hexdigest()
        resultado = validar_excel(archivo)
        if resultado['error_global']:
            importacion = ImportacionPreguntas.objects.create(
                usuario=request.user,
                archivo_nombre=archivo.name,
                archivo_hash=archivo_hash,
                estado=ImportacionPreguntas.ESTADO_FALLIDA,
                error_global=resultado['error_global'],
            )
            return Response(
                {
                    'detail': resultado['error_global'],
                    'importacion_id': importacion.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        filas = resultado['filas']
        validas = sum(1 for f in filas if f.valida)
        invalidas = len(filas) - validas
        importacion = ImportacionPreguntas.objects.create(
            usuario=request.user,
            archivo_nombre=archivo.name,
            archivo_hash=archivo_hash,
            estado=(
                ImportacionPreguntas.ESTADO_PREVIA
                if not invalidas
                else ImportacionPreguntas.ESTADO_ERROR
            ),
            total=len(filas),
            validas=validas,
            invalidas=invalidas,
        )
        FilaImportacionPregunta.objects.bulk_create([
            FilaImportacionPregunta(
                importacion=importacion,
                numero=f.numero,
                valida=f.valida,
                errores=f.errores,
                datos=f.datos,
            )
            for f in filas
        ])
        payload = {
            'importacion_id': importacion.id,
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
        importacion_id = request.data.get('importacion_id')
        if importacion_id:
            try:
                importacion = ImportacionPreguntas.objects.get(
                    pk=importacion_id,
                    usuario=request.user,
                )
            except ImportacionPreguntas.DoesNotExist:
                return Response(
                    {'detail': 'La importación no existe o no te pertenece.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if importacion.estado != ImportacionPreguntas.ESTADO_PREVIA:
                return Response(
                    {'detail': 'La importación no está lista para confirmar.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            filas = [
                FilaValidada(
                    numero=fila.numero,
                    errores=fila.errores,
                    datos=fila.datos,
                )
                for fila in importacion.filas.all()
            ]
        else:
            archivo = request.FILES.get('archivo')
            if not archivo:
                return Response(
                    {'detail': 'Debes enviar importacion_id.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            resultado = validar_excel(archivo)
            if resultado['error_global']:
                return Response(
                    {'detail': resultado['error_global']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            filas = resultado['filas']
            importacion = ImportacionPreguntas.objects.create(
                usuario=request.user,
                archivo_nombre=archivo.name,
                estado=ImportacionPreguntas.ESTADO_ERROR,
                total=len(filas),
                validas=sum(1 for f in filas if f.valida),
                invalidas=sum(1 for f in filas if not f.valida),
            )
            FilaImportacionPregunta.objects.bulk_create([
                FilaImportacionPregunta(
                    importacion=importacion,
                    numero=f.numero,
                    valida=f.valida,
                    errores=f.errores,
                    datos=f.datos,
                )
                for f in filas
            ])
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
                {'detail': str(e), 'importacion_id': importacion.id},
                status=status.HTTP_400_BAD_REQUEST,
            )
        importacion.estado = ImportacionPreguntas.ESTADO_CONFIRMADA
        importacion.preguntas_creadas = creadas
        importacion.confirmado_en = timezone.now()
        importacion.save(
            update_fields=('estado', 'preguntas_creadas', 'confirmado_en'),
        )
        return Response(
            {
                'detail': f'{creadas} preguntas importadas correctamente.',
                'importacion_id': importacion.id,
            },
            status=status.HTTP_201_CREATED,
        )