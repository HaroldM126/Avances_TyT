"""Crea datos demostrativos idempotentes para consultas y reportes."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
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
            question.categoria = category
            question.competencia = axis
            question.save(update_fields=('categoria', 'competencia'))
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
            correct.es_correcta = True
            correct.save(update_fields=('es_correcta',))
            incorrect.es_correcta = False
            incorrect.save(update_fields=('es_correcta',))
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
            if quiz.curso_id != course.pk:
                quiz.curso = course
                quiz.save(update_fields=('curso',))
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
            attempt, _ = Intento.objects.get_or_create(
                usuario=student,
                cuestionario=quiz,
                estado=Intento.ESTADO_ENVIADO,
                defaults={
                    'curso': course,
                    'periodo': course.periodo,
                    'fecha_inicio': now - timedelta(days=index),
                    'fecha_envio': now - timedelta(days=index),
                    'enviado': True,
                },
            )
            if not attempt.curso_id:
                attempt.curso = course
                attempt.periodo = course.periodo
                attempt.save(update_fields=('curso', 'periodo'))
            elif not attempt.periodo_id:
                attempt.periodo = course.periodo
                attempt.save(update_fields=('periodo',))
            for question_index, (question, correct, incorrect) in enumerate(questions):
                response, _ = RespuestaIntento.objects.get_or_create(
                    intento=attempt,
                    pregunta=question,
                )
                option = correct if (index + question_index) % 3 else incorrect
                response.opcion = option
                response.save(update_fields=('opcion',))
            attempt.puntaje = attempt.calcular_puntaje()
            attempt.enviado = True
            attempt.estado = Intento.ESTADO_ENVIADO
            attempt.fecha_envio = attempt.fecha_envio or now
            attempt.save(update_fields=(
                'puntaje',
                'enviado',
                'estado',
                'fecha_envio',
            ))

        for course, quiz in zip(courses, quizzes):
            student = next(
                student for student, enrolled_course in students
                if enrolled_course == course
            )
            ongoing, _ = Intento.objects.get_or_create(
                usuario=student,
                cuestionario=quiz,
                estado=Intento.ESTADO_EN_CURSO,
                defaults={'curso': course, 'periodo': course.periodo},
            )
            question, correct, _ = questions[0]
            response, _ = RespuestaIntento.objects.get_or_create(
                intento=ongoing,
                pregunta=question,
            )
            if response.opcion_id is None:
                response.opcion = correct
                response.save(update_fields=('opcion',))

        self.stdout.write(self.style.SUCCESS(
            'Datos de reportes listos: 2 años, 4 períodos, 2 cursos, '
            '6 estudiantes, 6 intentos finalizados y 2 en curso.'
        ))
