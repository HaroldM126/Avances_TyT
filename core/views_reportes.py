"""Vistas protegidas de consultas académicas y exportación."""

from datetime import date
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.http import FileResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Intento
from .permissions import has_active_permission
from .permissions import PuedeConfigurarCuestionarios
from .services.reportes import (
    aplicar_filtros,
    estado_intento_reporte,
    intento_finalizado,
    intentos_reporte,
    obtener_estadisticas_dificultad,
    obtener_estadisticas_eje,
    obtener_indicadores,
    obtener_opciones_filtros,
    obtener_promedios_estudiante,
    obtener_reporte,
    puede_consultar_todos,
    puede_consultar_propio,
    puede_ver_identificacion,
    _preparar_queryset_intentos,
    _intento_rows,
)


REPORT_TYPES = {
    'consolidado',
    'periodos',
    'cursos',
    'ejes',
    'calificaciones',
    'historial',
    'dificultad',
}
EXCEL_TYPES = {'consolidado', 'ejes', 'historial'}


class PuedeConsultarReportes(IsAuthenticated):
    message = 'No tienes permiso para consultar reportes.'

    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser
            or has_active_permission(request.user, 'ver_reportes')
            or puede_consultar_propio(request.user)
        )


class ReportPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'pagina'


class FiltrosReporteView(APIView):
    permission_classes = (PuedeConsultarReportes,)

    def get(self, request):
        return Response(obtener_opciones_filtros(request.query_params, request.user))


class ConsultaReporteView(APIView):
    permission_classes = (PuedeConsultarReportes,)
    pagination_class = ReportPagination

    def get(self, request):
        tipo = request.query_params.get('tipo', 'consolidado')
        if tipo not in REPORT_TYPES:
            raise ValidationError({'tipo': 'Tipo de consulta no válido.'})
        if request.query_params.get('ordenar', 'fecha') not in (
            'nombre',
            'fecha',
            'calificacion',
        ):
            raise ValidationError({
                'ordenar': 'Use nombre, fecha o calificacion.',
            })
        if request.query_params.get('direccion', 'desc') not in ('asc', 'desc'):
            raise ValidationError({'direccion': 'Use asc o desc.'})
        queryset = aplicar_filtros(
            intentos_reporte(),
            request.query_params,
            request.user,
        )
        indicadores = obtener_indicadores(queryset)
        umbrales = list(
            queryset.order_by()
            .values_list('cuestionario__nota_aprobar', flat=True)
            .distinct()
        )
        indicador_data = {
            **indicadores,
            'porcentaje_aprobacion': (
                round(
                    indicadores['aprobados']
                    * 100
                    / indicadores['intentos_finalizados'],
                    2,
                )
                if indicadores['intentos_finalizados']
                else 0
            ),
            'umbrales_aprobacion': [str(value) for value in umbrales],
        }
        rows = obtener_reporte(tipo, queryset, request.query_params, request.user)
        if tipo in ('consolidado', 'calificaciones'):
            rows = _preparar_queryset_intentos(
                rows,
                incluir_identificacion=puede_ver_identificacion(request.user),
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request, view=self)
        if tipo in ('consolidado', 'calificaciones'):
            page = _intento_rows(
                page,
                incluir_identificacion=puede_ver_identificacion(request.user),
            )
        else:
            page = list(page)
        if tipo == 'ejes':
            page = [obtener_estadisticas_eje(row) for row in page]
        elif tipo == 'dificultad':
            page = [obtener_estadisticas_dificultad(row) for row in page]
        elif tipo == 'historial':
            for row in page:
                row['fecha'] = row['fecha_envio'] or row['fecha_inicio']
                row['estado'] = estado_intento_reporte(
                    row['estado'],
                    row['enviado'],
                    row['fecha_envio'],
                    row['puntaje'],
                )
                if not intento_finalizado(
                    row['enviado'],
                    row['fecha_envio'],
                    row['puntaje'],
                ):
                    row['puntaje'] = None
                row.pop('enviado')
        return Response({
            'count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': page,
            'indicadores': indicador_data,
            'umbral_aprobacion': 'Configurado por cuestionario',
            'exclusion': (
                'Se excluyen intentos no finalizados o sin calificación.'
            ),
        })


class HistorialEstudianteView(APIView):
    permission_classes = (PuedeConsultarReportes,)

    def get(self, request, estudiante_id):
        params = request.query_params.copy()
        params['estudiante'] = str(estudiante_id)
        queryset = aplicar_filtros(
            intentos_reporte(),
            params,
            request.user,
        )
        rows = list(obtener_reporte('historial', queryset, params, request.user))
        for row in rows:
            row['fecha'] = row['fecha_envio'] or row['fecha_inicio']
            row['estado'] = estado_intento_reporte(
                row['estado'],
                row['enviado'],
                row['fecha_envio'],
                row['puntaje'],
            )
            if not intento_finalizado(
                row['enviado'],
                row['fecha_envio'],
                row['puntaje'],
            ):
                row['puntaje'] = None
            row.pop('enviado')
        return Response(rows)


def _active_filters(params):
    labels = (
        ('anio', 'Año'),
        ('periodo', 'Período'),
        ('curso', 'Curso'),
        ('eje', 'Eje'),
        ('estudiante', 'Estudiante'),
        ('buscar', 'Búsqueda'),
    )
    active = [
        f'{label}: {params.get(key)}'
        for key, label in labels
        if params.get(key)
    ]
    return '; '.join(active) if active else 'Todos'


def _threshold_description(queryset):
    values = list(
        queryset.order_by()
        .values_list('cuestionario__nota_aprobar', flat=True)
        .distinct()
    )
    if not values:
        return 'Nota mínima configurada en cada cuestionario (sin resultados).'
    return 'Nota mínima por cuestionario: ' + ', '.join(
        str(value) for value in values
    )


def _estado_legible(estado):
    return dict(Intento.ESTADO_CHOICES).get(estado, estado)


def _write_sheet(workbook, title, headers, rows, generated, filters, threshold):
    sheet = workbook.create_sheet(title=title)
    sheet.append([title])
    sheet.append([f'Fecha de generación: {generated}'])
    sheet.append([f'Filtros activos: {filters}'])
    sheet.append([f'Umbral de aprobación: {threshold}'])
    sheet.append([
        'Las métricas excluyen los intentos no finalizados o sin nota; '
        'esos intentos se listan con calificación —.'
    ])
    sheet.append([])
    sheet.append(headers)

    for cell in sheet[7]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='124A69')
        cell.alignment = Alignment(wrap_text=True, vertical='center')

    if rows:
        for row in rows:
            sheet.append([
                (
                    timezone.localtime(value).replace(tzinfo=None)
                    if isinstance(value, datetime) and timezone.is_aware(value)
                    else value
                )
                for value in row
            ])
    else:
        sheet.append(['Sin resultados'])

    sheet.freeze_panes = 'A8'
    sheet.auto_filter.ref = f'A7:{_column_letter(len(headers))}{max(sheet.max_row, 7)}'
    for column in sheet.iter_cols(
        min_row=7,
        max_row=7 + len(rows),
        min_col=1,
        max_col=len(headers),
    ):
        width = min(
            48,
            max(
                8,
                max(
                    len(str(cell.value or ''))
                    for cell in column
                ) + 2,
            ),
        )
        sheet.column_dimensions[column[0].column_letter].width = width
    for row in sheet.iter_rows(min_row=8):
        for cell in row:
            if isinstance(cell.value, (float, Decimal)):
                cell.number_format = '0.00'
    sheet['A1'].font = Font(bold=True, size=14, color='124A69')


def _column_letter(number):
    result = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _consolidated_excel_rows(queryset, user, params):
    rows = _intento_rows(
        _preparar_queryset_intentos(
            obtener_reporte(
                'consolidado',
                queryset,
                params,
                user=user,
            ),
            incluir_identificacion=puede_ver_identificacion(user),
        ),
        incluir_identificacion=puede_ver_identificacion(user),
    )
    show_id = puede_ver_identificacion(user)
    table = []
    for row in rows:
        values = [
            row['anio'] or '',
            row['periodo'],
            row['curso'],
            row['estudiante'],
        ]
        if show_id:
            values.append(row.get('identificacion', ''))
        values.extend([
            row['simulacro'],
            row['fecha'],
            row['calificacion'] if row['calificacion'] is not None else '—',
            _estado_legible(row['estado']),
            row['nota_aprobar'],
        ])
        table.append(values)
    return table


class ExportarReporteView(APIView):
    permission_classes = (PuedeConsultarReportes,)

    def get(self, request, tipo):
        if tipo not in EXCEL_TYPES:
            raise ValidationError({
                'tipo': 'Exporta consolidado, ejes o historial.',
            })
        if request.query_params.get('ordenar', 'fecha') not in (
            'nombre',
            'fecha',
            'calificacion',
        ):
            raise ValidationError({
                'ordenar': 'Use nombre, fecha o calificacion.',
            })
        if request.query_params.get('direccion', 'desc') not in ('asc', 'desc'):
            raise ValidationError({'direccion': 'Use asc o desc.'})
        params = request.query_params.copy()
        if tipo == 'historial' and not params.get('estudiante'):
            if puede_consultar_todos(request.user):
                raise ValidationError({
                    'estudiante': 'Selecciona un estudiante para exportar su historial.',
                })
            params['estudiante'] = str(request.user.pk)
        queryset = aplicar_filtros(
            intentos_reporte(),
            params,
            request.user,
        )

        if tipo == 'consolidado':
            rows = _consolidated_excel_rows(
                queryset,
                request.user,
                params,
            )
            headers = [
                'Año',
                'Período',
                'Curso',
                'Estudiante',
            ]
            if puede_ver_identificacion(request.user):
                headers.append('Identificación')
            headers.extend([
                'Simulacro',
                'Fecha',
                'Calificación',
                'Estado',
                'Nota mínima de aprobación',
            ])
        elif tipo == 'ejes':
            rows = [
                [
                    row['anio'],
                    row['periodo'],
                    row['curso'],
                    row['eje'],
                    row['respuestas_registradas'],
                    row['aciertos'],
                    row['errores'],
                    row['porcentaje_aciertos'],
                    None,
                ]
                for row in (
                    {
                        'anio': item.get('intento__periodo__anio'),
                        'periodo': item.get('intento__periodo__nombre'),
                        'curso': item.get('intento__curso__nombre'),
                        'eje': item['pregunta__competencia__nombre'],
                        **obtener_estadisticas_eje(item),
                    }
                    for item in obtener_reporte('ejes', queryset, params, request.user)
                )
            ]
            headers = [
                'Año', 'Período', 'Curso', 'Eje', 'Respuestas registradas',
                'Aciertos', 'Errores', '% de aciertos', 'Nota promedio',
            ]
        else:
            history = obtener_reporte('historial', queryset, params, request.user)
            rows = []
            for item in history:
                result_date = item['fecha_envio'] or item['fecha_inicio']
                completed = intento_finalizado(
                    item['enviado'],
                    item['fecha_envio'],
                    item['puntaje'],
                )
                grade = item['puntaje'] if completed else '—'
                student = (
                    f"{item['usuario__first_name']} {item['usuario__last_name']}".strip()
                    or item['usuario__username']
                )
                answered = item['preguntas_respondidas']
                rows.append([
                    student,
                    item['curso__nombre'] or '',
                    item['periodo__nombre'] or '',
                    item['cuestionario__nombre'],
                    result_date,
                    answered,
                    item['aciertos'],
                    answered - item['aciertos'],
                    grade,
                    _estado_legible(estado_intento_reporte(
                        item['estado'],
                        item['enviado'],
                        item['fecha_envio'],
                        item['puntaje'],
                    )),
                ])
            headers = [
                'Estudiante', 'Curso', 'Período', 'Simulacro', 'Fecha',
                'Preguntas respondidas', 'Aciertos', 'Errores', 'Nota final',
                'Estado',
            ]

        generated = timezone.localtime().replace(
            second=0,
            microsecond=0,
        ).strftime('%d/%m/%Y %H:%M')
        threshold = _threshold_description(queryset)
        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)
        _write_sheet(
            workbook,
            {'consolidado': 'Consolidado general', 'ejes': 'Desempeño por eje',
             'historial': 'Historial individual'}[tipo],
            headers,
            rows,
            generated,
            _active_filters(params),
            threshold,
        )

        if tipo == 'consolidado':
            averages = obtener_promedios_estudiante(
                queryset,
                incluir_identificacion=puede_ver_identificacion(request.user),
            )
            average_headers = ['Estudiante']
            if puede_ver_identificacion(request.user):
                average_headers.append('Identificación')
            average_headers.append('Promedio')
            average_rows = []
            for item in averages:
                average_row = [item['estudiante']]
                if puede_ver_identificacion(request.user):
                    average_row.append(item.get('identificacion', ''))
                average_row.append(item['promedio'])
                average_rows.append(average_row)
            _write_sheet(
                workbook,
                'Promedio por estudiante',
                average_headers,
                average_rows,
                generated,
                _active_filters(params),
                threshold,
            )

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        period_name = ''
        if params.get('periodo'):
            from .models import PeriodoAcademico
            period = PeriodoAcademico.objects.filter(
                pk=params['periodo'],
            ).values_list('nombre', flat=True).first()
            if period:
                period_name = '_' + period.replace('-', '-')
        elif params.get('anio'):
            period_name = '_' + str(params['anio'])
        else:
            period_name = '_todos'
        stamp = date.today().strftime('%Y%m%d')
        filename = f'reporte_{tipo}{period_name}_{stamp}.xlsx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type=(
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet'
            ),
        )


class CursosAcademicosView(APIView):
    permission_classes = (IsAuthenticated, PuedeConfigurarCuestionarios)

    def get(self, request):
        from .models import CursoGrupo

        courses = CursoGrupo.objects.select_related('periodo').order_by(
            '-periodo__anio',
            'periodo__nombre',
            'nombre',
        )
        return Response([
            {
                'id': course.id,
                'nombre': course.nombre,
                'periodo': course.periodo.nombre,
            }
            for course in courses
        ])
