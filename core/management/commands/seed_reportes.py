"""Crea datos demostrativos idempotentes para consultas y reportes."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from core.models import (
    Categoria,
    Competencia,
    Cuestionario,
    CuestionarioPregunta,
    CursoGrupo,
    Intento,
    Matricula,
    OpcionRespuesta,
    PeriodoAcademico,
    Pregunta,
    RespuestaIntento,
)


EJES = (
    'Lectura crítica',
    'Comprensión ciudadana',
    'Pensamiento crítico',
)


class Command(BaseCommand):
    help = 'Crea períodos, cursos, estudiantes y resultados de ejemplo.'

    def handle(self, *args, **options):
        periods = {}
        for year in (2025, 2026):
            for term in (1, 2):
                name = f'{year}-{term}'
                periods[name], _ = PeriodoAcademico.objects.get_or_create(
                    nombre=name,
                    defaults={'anio': year},
                )

        courses = []
        for name, period_name in (
            ('Grupo TyT A', '2026-1'),
            ('Grupo TyT B', '2026-2'),
        ):
            course, _ = CursoGrupo.objects.get_or_create(
                periodo=periods[period_name],
                nombre=name,
            )
            courses.append(course)

        student_group, _ = Group.objects.get_or_create(name='Estudiante')
        now = timezone.now()
        category, _ = Categoria.objects.get_or_create(nombre='Competencias TyT')
        questions = []
        for index, name in enumerate(EJES, start=1):
            axis, _ = Competencia.objects.get_or_create(nombre=name)
            question, _ = Pregunta.objects.get_or_create(
                enunciado=f'[DEMO TyT] Pregunta de {name.lower()}',
                defaults={
                    'categoria': category,
                    'competencia': axis,
                    'texto_base': 'Situación de demostración',
                    'puntaje': Decimal('1.00'),
                    'activa': True,
                },
            )
            correct, _ = OpcionRespuesta.objects.get_or_create(
                pregunta=question,
                texto=f'Respuesta correcta {index}',
                defaults={'es_correcta': True, 'orden': 1},
            )
            incorrect, _ = OpcionRespuesta.objects.get_or_create(
                pregunta=question,
                texto=f'Respuesta incorrecta {index}',
                defaults={'es_correcta': False, 'orden': 2},
            )
            questions.append((question, correct, incorrect))

        quizzes = []
        for course in courses:
            quiz, _ = Cuestionario.objects.get_or_create(
                nombre=f'[DEMO] Simulacro {course.nombre}',
                defaults={
                    'curso': course,
                    'fecha_apertura': now - timedelta(days=30),
                    'fecha_cierre': now + timedelta(days=365),
                    'duracion_minutos': 60,
                    'max_intentos': 3,
                    'nota_maxima': Decimal('5.00'),
                    'nota_aprobar': Decimal('3.00'),
                    'permitir_revision': True,
                    'activo': True,
                },
            )
            for order, (question, _, _) in enumerate(questions, start=1):
                CuestionarioPregunta.objects.get_or_create(
                    cuestionario=quiz,
                    pregunta=question,
                    defaults={'orden': order},
                )
            quizzes.append(quiz)

        students = []
        for index in range(1, 7):
            username = f'demo_estudiante_{index}'
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': f'Estudiante {index}',
                    'last_name': 'Demostración',
                    'email': f'demo{index}@example.invalid',
                    'is_active': True,
                },
            )
            if created:
                student.set_password('TyT-Demo-2026!')
                student.save(update_fields=('password',))
            student.groups.add(student_group)
            course = courses[(index - 1) // 3]
            Matricula.objects.get_or_create(
                estudiante=student,
                curso=course,
                defaults={
                    'identificacion': f'DEMO-{index:04d}',
                    'activa': True,
                },
            )
            students.append((student, course))

        for index, (student, course) in enumerate(students, start=1):
            quiz = quizzes[courses.index(course)]
            attempt = Intento.objects.filter(
                usuario=student,
                cuestionario=quiz,
                estado=Intento.ESTADO_ENVIADO,
            ).order_by('pk').first()
            created = attempt is None
            if created:
                attempt = Intento.objects.create(
                    usuario=student,
                    cuestionario=quiz,
                    curso=course,
                    periodo=course.periodo,
                    fecha_envio=now - timedelta(days=index),
                    enviado=True,
                    estado=Intento.ESTADO_ENVIADO,
                )
            if created:
                for question_index, (question, correct, incorrect) in enumerate(questions):
                    option = correct if (index + question_index) % 3 else incorrect
                    RespuestaIntento.objects.create(
                        intento=attempt,
                        pregunta=question,
                        opcion=option,
                    )
                attempt.puntaje = attempt.calcular_puntaje()
                attempt.save(update_fields=('puntaje',))

        pagination_questions = []
        for index, name in enumerate(EJES):
            axis = Competencia.objects.get(nombre=name)
            question, _ = Pregunta.objects.get_or_create(
                enunciado=f'[DEMO PAGINACIÓN] Pregunta de {name.lower()}',
                defaults={
                    'categoria': category,
                    'competencia': axis,
                    'texto_base': 'Situación para demostrar la paginación',
                    'puntaje': Decimal(('0.90', '1.00', '1.10')[index]),
                    'activa': True,
                },
            )
            correct, _ = OpcionRespuesta.objects.get_or_create(
                pregunta=question,
                texto=f'Respuesta correcta paginación {index + 1}',
                defaults={'es_correcta': True, 'orden': 1},
            )
            incorrect, _ = OpcionRespuesta.objects.get_or_create(
                pregunta=question,
                texto=f'Respuesta incorrecta paginación {index + 1}',
                defaults={'es_correcta': False, 'orden': 2},
            )
            pagination_questions.append((question, correct, incorrect))

        grade_patterns = (
            (0,),
            (0, 1),
            (0, 2),
            (1, 2),
            (0, 1, 2),
            (1,),
        )
        for course_index, course in enumerate(courses):
            students_in_course = [
                (student, student_course)
                for student, student_course in students
                if student_course == course
            ]
            pagination_quizzes = []
            for quiz_number in range(1, 4):
                quiz, _ = Cuestionario.objects.get_or_create(
                    nombre=(
                        f'[DEMO PAGINACIÓN] Simulacro {course.nombre} '
                        f'{quiz_number}'
                    ),
                    defaults={
                        'curso': course,
                        'fecha_apertura': now - timedelta(days=30),
                        'fecha_cierre': now + timedelta(days=365),
                        'duracion_minutos': 60,
                        'max_intentos': 10,
                        'nota_maxima': Decimal('5.00'),
                        'nota_aprobar': Decimal('3.00'),
                        'permitir_revision': True,
                        'activo': True,
                    },
                )
                for order, (question, _, _) in enumerate(
                    pagination_questions,
                    start=1,
                ):
                    CuestionarioPregunta.objects.get_or_create(
                        cuestionario=quiz,
                        pregunta=question,
                        defaults={'orden': order},
                    )
                pagination_quizzes.append(quiz)

            for student, _ in students_in_course:
                student_number = int(student.username.rsplit('_', 1)[1]) - 1
                for quiz_number, quiz in enumerate(pagination_quizzes):
                    attempt, created = Intento.objects.get_or_create(
                        usuario=student,
                        cuestionario=quiz,
                        defaults={
                            'curso': course,
                            'periodo': course.periodo,
                            'enviado': True,
                            'estado': Intento.ESTADO_ENVIADO,
                            'fecha_envio': now - timedelta(
                                days=student_number + quiz_number + 1,
                            ),
                        },
                    )
                    if not created:
                        continue

                    correct_questions = grade_patterns[
                        (student_number + quiz_number + course_index)
                        % len(grade_patterns)
                    ]
                    for question_index, (
                        question,
                        correct,
                        incorrect,
                    ) in enumerate(pagination_questions):
                        RespuestaIntento.objects.create(
                            intento=attempt,
                            pregunta=question,
                            opcion=(
                                correct
                                if question_index in correct_questions
                                else incorrect
                            ),
                        )
                    attempt.puntaje = attempt.calcular_puntaje()
                    attempt.save(update_fields=('puntaje',))

        for course, quiz in zip(courses, quizzes):
            student = next(
                student for student, enrolled_course in students
                if enrolled_course == course
            )
            ongoing = Intento.objects.filter(
                usuario=student,
                cuestionario=quiz,
                estado=Intento.ESTADO_EN_CURSO,
            ).order_by('pk').first()
            created = ongoing is None
            if created:
                ongoing = Intento.objects.create(
                    usuario=student,
                    cuestionario=quiz,
                    curso=course,
                    periodo=course.periodo,
                    estado=Intento.ESTADO_EN_CURSO,
                )
            if created:
                question, correct, _ = questions[0]
                RespuestaIntento.objects.create(
                    intento=ongoing,
                    pregunta=question,
                    opcion=correct,
                )

        demo_attempts = Intento.objects.filter(
            usuario__username__startswith='demo_estudiante_',
            enviado=True,
            fecha_envio__isnull=False,
            puntaje__isnull=False,
        ).filter(
            Q(cuestionario__nombre__startswith='[DEMO] Simulacro')
            | Q(cuestionario__nombre__startswith='[DEMO PAGINACIÓN]')
        ).count()
        self.stdout.write(self.style.SUCCESS(
            'Datos de reportes listos: 2 años, 4 períodos, 2 cursos, '
            f'6 estudiantes, {demo_attempts} intentos finalizados '
            'y 2 en curso.'
        ))
