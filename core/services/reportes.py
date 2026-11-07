"""Consultas y agregaciones ORM del módulo de reportes."""

from django.contrib.auth import get_user_model
from django.db.models import (
    Avg,
    Count,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce
from rest_framework.exceptions import NotFound, ValidationError

from core.models import (
    Competencia,
    CursoGrupo,
    Intento,
    Matricula,
    PeriodoAcademico,
    Pregunta,
    RespuestaIntento,
)
from core.permissions import has_active_permission


PAGE_SIZE = 10
MAX_SEARCH_LENGTH = 100


def puede_consultar_todos(user):
    return user.is_superuser or has_active_permission(user, 'ver_reportes')


def puede_consultar_propio(user):
    return user.groups.filter(
        name='Estudiante',
        rol__activo=True,
    ).exists()


def puede_ver_identificacion(user):
    return user.is_superuser or has_active_permission(
        user,
        'ver_identificacion_estudiante',
    )


def intentos_reporte():
    """Devuelve intentos para consultas históricas sin calcular métricas."""
    return Intento.objects.select_related(
        'usuario',
        'cuestionario',
        'curso',
        'periodo',
    )


def intentos_finalizados(queryset=None):
    """Limita promedios e indicadores a intentos enviados con nota."""
    # Los intentos en curso o sin calificación se excluyen de las métricas.
    queryset = queryset if queryset is not None else intentos_reporte()
    return queryset.filter(criterio_finalizacion_intento())


def criterio_finalizacion_intento():
    """Criterio único de finalización para agregaciones y presentación."""
    return Q(
        enviado=True,
        fecha_envio__isnull=False,
        puntaje__isnull=False,
    )


def intento_finalizado(enviado, fecha_envio, puntaje):
    """Aplica a una fila el mismo criterio usado por las consultas ORM."""
    return enviado and fecha_envio is not None and puntaje is not None


def estado_intento_reporte(estado, enviado, fecha_envio, puntaje):
    """Evita mostrar como en curso un intento que cumple la finalización."""
    if (
        estado == Intento.ESTADO_EN_CURSO
        and intento_finalizado(enviado, fecha_envio, puntaje)
    ):
        return Intento.ESTADO_ENVIADO
    return estado


def _id_param(params, name):
    value = params.get(name)
    if value in (None, ''):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: 'Debe ser un identificador válido.'})
    if parsed <= 0:
        raise ValidationError({name: 'Debe ser un identificador positivo.'})
    return parsed


def aplicar_filtros(queryset, params, user):
    """Aplica filtros académicos y protege el alcance de cada usuario."""
    year = params.get('anio') or ''
    if year:
        try:
            year_number = int(year)
        except (TypeError, ValueError):
            raise ValidationError({'anio': 'El año debe ser numérico.'})
        if year_number < 1900 or year_number > 9999:
            raise ValidationError({'anio': 'El año indicado no es válido.'})
        queryset = queryset.filter(periodo__anio=year_number)

    period_id = _id_param(params, 'periodo')
    if period_id:
        period = PeriodoAcademico.objects.filter(pk=period_id).first()
        if period is None:
            raise NotFound('El período indicado no existe.')
        if year and period.anio != int(year):
            raise ValidationError({
                'periodo': 'El período no pertenece al año seleccionado.',
            })
        queryset = queryset.filter(periodo_id=period_id)

    course_id = _id_param(params, 'curso')
    if course_id:
        course = CursoGrupo.objects.select_related('periodo').filter(
            pk=course_id,
        ).first()
        if course is None:
            raise NotFound('El curso indicado no existe.')
        if period_id and course.periodo_id != period_id:
            raise ValidationError({
                'curso': 'El curso no pertenece al período seleccionado.',
            })
        if year and course.periodo.anio != int(year):
            raise ValidationError({
                'curso': 'El curso no pertenece al año seleccionado.',
            })
        if not puede_consultar_todos(user) and not Matricula.objects.filter(
            estudiante=user,
            curso_id=course_id,
            activa=True,
        ).exists():
            raise NotFound('No se encontró el curso solicitado.')
        queryset = queryset.filter(curso_id=course_id)

    axis_id = _id_param(params, 'eje')
    if axis_id:
        if not Competencia.objects.filter(pk=axis_id).exists():
            raise NotFound('El eje temático indicado no existe.')
        if not queryset.filter(
            cuestionario__cuestionario_preguntas__pregunta__competencia_id=axis_id,
        ).exists():
            raise NotFound('El eje no está disponible en los filtros seleccionados.')
        queryset = queryset.filter(
            cuestionario__cuestionario_preguntas__pregunta__competencia_id=axis_id,
        )

    student_id = _id_param(params, 'estudiante')
    if student_id:
        if not puede_consultar_todos(user) and student_id != user.pk:
            raise NotFound('No se encontró el estudiante solicitado.')
        User = get_user_model()
        if not User.objects.filter(pk=student_id).exists():
            raise NotFound('No se encontró el estudiante solicitado.')
        queryset = queryset.filter(usuario_id=student_id)
    elif not puede_consultar_todos(user):
        queryset = queryset.filter(usuario=user)

    search = params.get('buscar', '')
    if search:
        search = str(search).strip()
        if len(search) > MAX_SEARCH_LENGTH:
            raise ValidationError({
                'buscar': f'La búsqueda no puede superar {MAX_SEARCH_LENGTH} caracteres.',
            })
        if search:
            queryset = queryset.filter(
                Q(usuario__first_name__icontains=search)
                | Q(usuario__last_name__icontains=search)
                | Q(usuario__username__icontains=search)
                | Q(usuario__email__icontains=search)
                | Q(
                    usuario__matriculas__identificacion__icontains=search,
                    usuario__matriculas__activa=True,
                )
            )

    return queryset.distinct()


def obtener_indicadores(queryset):
    """Calcula métricas sobre intentos finalizados y notas disponibles."""
    return intentos_finalizados(queryset).aggregate(
        estudiantes_distintos=Count('usuario_id', distinct=True),
        intentos_finalizados=Count('id'),
        promedio=Avg('puntaje'),
        minima=Min('puntaje'),
        maxima=Max('puntaje'),
        aprobados=Count(
            'id',
            filter=Q(puntaje__gte=F('cuestionario__nota_aprobar')),
        ),
        no_aprobados=Count(
            'id',
            filter=Q(puntaje__lt=F('cuestionario__nota_aprobar')),
        ),
    )


def obtener_opciones_filtros(params, user):
    """Construye opciones compatibles desde los filtros padre hacia abajo."""
    base = aplicar_filtros(intentos_reporte(), {}, user)
    years = list(
        base.exclude(periodo__isnull=True)
        .values_list('periodo__anio', flat=True)
        .distinct()
        .order_by('-periodo__anio')
    )

    year_scope = aplicar_filtros(
        base,
        {'anio': params.get('anio', '')},
        user,
    )
    periods = PeriodoAcademico.objects.filter(
        intentos__in=year_scope,
    ).distinct().order_by('-anio', 'nombre')

    period_scope = aplicar_filtros(
        base,
        {
            'anio': params.get('anio', ''),
            'periodo': params.get('periodo', ''),
        },
        user,
    )
    courses = CursoGrupo.objects.filter(
        intentos__in=period_scope,
    ).select_related('periodo').distinct().order_by('nombre')

    course_scope = aplicar_filtros(
        base,
        {
            'anio': params.get('anio', ''),
            'periodo': params.get('periodo', ''),
            'curso': params.get('curso', ''),
        },
        user,
    )
    quiz_questions = Pregunta.objects.filter(
        cuestionario_preguntas__cuestionario__intento__in=course_scope,
        competencia__isnull=False,
    ).select_related('competencia').distinct()
    axes = Competencia.objects.filter(
        preguntas__in=quiz_questions,
    ).distinct().order_by('nombre')

    student_params = {
        key: params.get(key, '')
        for key in ('anio', 'periodo', 'curso', 'eje')
    }
    student_scope = aplicar_filtros(base, student_params, user)
    User = get_user_model()
    if params.get('curso'):
        # La lista de estudiantes de un grupo se limita a matrículas activas.
        enrolled = Matricula.objects.filter(
            curso_id=params['curso'],
            activa=True,
        ).values('estudiante_id')
        students = User.objects.filter(
            pk__in=enrolled,
            intento__in=student_scope,
        ).distinct()
    else:
        students = User.objects.filter(
            intento__in=student_scope,
        ).distinct()
    if not puede_consultar_todos(user):
        students = students.filter(pk=user.pk)
    students = students.order_by('last_name', 'first_name', 'username')
    search = str(params.get('buscar', '')).strip()
    if search:
        if len(search) > MAX_SEARCH_LENGTH:
            raise ValidationError({
                'buscar': f'La búsqueda no puede superar {MAX_SEARCH_LENGTH} caracteres.',
            })
        students = students.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(matriculas__identificacion__icontains=search, matriculas__activa=True)
        ).distinct()

    return {
        'anios': years,
        'periodos': [
            {'id': item.id, 'nombre': item.nombre, 'anio': item.anio}
            for item in periods
        ],
        'cursos': [
            {
                'id': item.id,
                'nombre': item.nombre,
                'periodo_id': item.periodo_id,
                'periodo': item.periodo.nombre,
            }
            for item in courses
        ],
        'ejes': [{'id': item.id, 'nombre': item.nombre} for item in axes],
        'estudiantes': [
            {
                'id': item.id,
                'nombre': (
                    f'{item.first_name} {item.last_name}'.strip()
                    or item.username
                ),
                'usuario': item.username,
            }
            for item in students
        ],
    }


def ordenar_intentos(queryset, params):
    sort = params.get('ordenar', 'fecha')
    direction = params.get('direccion', 'desc')
    fields = {
        'nombre': ('usuario__last_name', 'usuario__first_name'),
        'fecha': ('fecha_envio',),
        'calificacion': ('puntaje',),
    }
    if sort not in fields:
        raise ValidationError({
            'ordenar': 'Use nombre, fecha o calificacion.',
        })
    if direction not in ('asc', 'desc'):
        raise ValidationError({'direccion': 'Use asc o desc.'})
    if sort == 'fecha':
        queryset = queryset.annotate(
            fecha_orden=Coalesce('fecha_envio', 'fecha_inicio'),
        )
        fields['fecha'] = ('fecha_orden',)
    prefix = '-' if direction == 'desc' else ''
    return queryset.order_by(
        *(f'{prefix}{field}' for field in fields[sort]),
        'pk',
    )


def _preparar_queryset_intentos(queryset, incluir_identificacion=False):
    queryset = queryset.select_related(
        'usuario',
        'curso',
        'periodo',
        'cuestionario',
    )
    if incluir_identificacion:
        queryset = queryset.annotate(
            identificacion_estudiante=Subquery(
                Matricula.objects.filter(
                    estudiante_id=OuterRef('usuario_id'),
                    curso_id=OuterRef('curso_id'),
                ).values('identificacion')[:1],
            ),
        )
    return queryset


def _intento_rows(queryset, incluir_identificacion=False):
    rows = []
    for intento in queryset:
        row = {
            'id': intento.id,
            'estudiante_id': intento.usuario_id,
            'estudiante': (
                f'{intento.usuario.first_name} {intento.usuario.last_name}'.strip()
                or intento.usuario.username
            ),
            'curso': intento.curso.nombre if intento.curso else '',
            'periodo': (
                intento.periodo.nombre
                if intento.periodo_id
                else ''
            ),
            'anio': (
                intento.periodo.anio
                if intento.periodo_id
                else None
            ),
            'simulacro': intento.cuestionario.nombre,
            'fecha': intento.fecha_envio or intento.fecha_inicio,
            'calificacion': intento.puntaje,
            'estado': estado_intento_reporte(
                intento.estado,
                intento.enviado,
                intento.fecha_envio,
                intento.puntaje,
            ),
            'nota_aprobar': intento.cuestionario.nota_aprobar,
        }
        if not intento_finalizado(
            intento.enviado,
            intento.fecha_envio,
            intento.puntaje,
        ):
            row['calificacion'] = None
        if incluir_identificacion:
            row['identificacion'] = intento.identificacion_estudiante or ''
        rows.append(row)
    return rows


def _respuestas_por_intento(queryset):
    ids = queryset.values('pk')
    return RespuestaIntento.objects.filter(
        intento_id__in=ids,
        opcion__isnull=False,
    )


def obtener_reporte(tipo, queryset, params, user):
    """Ejecuta una de las siete consultas del módulo con el ORM."""
    if tipo in ('consolidado', 'calificaciones'):
        return ordenar_intentos(queryset, params)

    if tipo == 'periodos':
        return (
            intentos_finalizados(queryset)
            .exclude(periodo__isnull=True)
            .values(
                'periodo_id',
                'periodo__anio',
                'periodo__nombre',
            )
            .annotate(
                evaluaciones=Count('id'),
                promedio=Avg('puntaje'),
            )
            .order_by('-periodo__anio', 'periodo__nombre')
        )

    if tipo == 'cursos':
        return (
            intentos_finalizados(queryset)
            .exclude(curso__isnull=True)
            .values('curso_id', 'curso__nombre', 'periodo__nombre')
            .annotate(
                estudiantes_distintos=Count('usuario_id', distinct=True),
                intentos_finalizados=Count('id'),
                promedio=Avg('puntaje'),
                minima=Min('puntaje'),
                maxima=Max('puntaje'),
            )
            .order_by('periodo__nombre', 'curso__nombre')
        )

    if tipo == 'ejes':
        answered = _respuestas_por_intento(queryset).exclude(
            pregunta__competencia__isnull=True,
        )
        axis_id = _id_param(params, 'eje')
        if axis_id:
            answered = answered.filter(pregunta__competencia_id=axis_id)
        return (
            answered.values(
                'intento__periodo__anio',
                'intento__periodo__nombre',
                'intento__curso__nombre',
                'pregunta__competencia_id',
                'pregunta__competencia__nombre',
            )
            .annotate(
                respuestas_registradas=Count('id'),
                aciertos=Count('id', filter=Q(opcion__es_correcta=True)),
            )
            .order_by('pregunta__competencia__nombre')
        )

    if tipo == 'historial':
        student_id = _id_param(params, 'estudiante')
        if student_id is None:
            if puede_consultar_todos(user):
                raise ValidationError({
                    'estudiante': 'Selecciona un estudiante para consultar su historial.',
                })
            student_id = user.pk
        return (
            queryset.filter(usuario_id=student_id)
            .annotate(
                preguntas_respondidas=Count(
                    'respuestaintento',
                    filter=Q(respuestaintento__opcion__isnull=False),
                ),
                aciertos=Count(
                    'respuestaintento',
                    filter=Q(respuestaintento__opcion__es_correcta=True),
                ),
            )
            .order_by('fecha_inicio', 'pk')
            .values(
                'id',
                'usuario_id',
                'usuario__first_name',
                'usuario__last_name',
                'usuario__username',
                'curso__nombre',
                'periodo__nombre',
                'cuestionario__nombre',
                'fecha_inicio',
                'fecha_envio',
                'enviado',
                'puntaje',
                'estado',
                'preguntas_respondidas',
                'aciertos',
            )
        )

    if tipo == 'dificultad':
        answered = _respuestas_por_intento(queryset)
        axis_id = _id_param(params, 'eje')
        if axis_id:
            answered = answered.filter(pregunta__competencia_id=axis_id)
        return (
            answered.values(
                'pregunta_id',
                'pregunta__enunciado',
                'pregunta__competencia__nombre',
            )
            .annotate(
                respuestas_registradas=Count('id'),
                aciertos=Count('id', filter=Q(opcion__es_correcta=True)),
            )
            .order_by('aciertos', 'pregunta__enunciado')
        )

    raise ValidationError({
        'tipo': 'Tipo de consulta no válido.',
    })


def obtener_promedios_estudiante(queryset, incluir_identificacion=False):
    """Promedios por estudiante calculados en la base de datos."""
    aggregate = intentos_finalizados(queryset).values(
            'usuario_id',
            'usuario__first_name',
            'usuario__last_name',
            'usuario__username',
        ).annotate(promedio=Avg('puntaje'))
    if incluir_identificacion:
        aggregate = aggregate.annotate(
            identificacion=Subquery(
                Matricula.objects.filter(
                    activa=True,
                    estudiante_id=OuterRef('usuario_id'),
                ).values('identificacion')[:1],
            ),
        )
    rows = list(
        aggregate.order_by('usuario__last_name', 'usuario__first_name')
    )
    for row in rows:
        row['estudiante'] = (
            f"{row.pop('usuario__first_name')} {row.pop('usuario__last_name')}".strip()
            or row.pop('usuario__username')
        )
    return rows


def obtener_estadisticas_eje(row):
    """Añade porcentaje sin inferir una nota que el dominio no define."""
    total = row['respuestas_registradas']
    return {
        **row,
        'porcentaje_aciertos': round(row['aciertos'] * 100 / total, 2) if total else 0,
        'errores': total - row['aciertos'],
        'nota_promedio': None,
    }


def obtener_estadisticas_dificultad(row):
    total = row['respuestas_registradas']
    return {
        **row,
        'errores': total - row['aciertos'],
        'porcentaje_aciertos': round(row['aciertos'] * 100 / total, 2) if total else 0,
    }
