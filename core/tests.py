from django.contrib.auth.models import Group, Permission, User
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from openpyxl import load_workbook

from .models import (
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


class AuthenticationAndRolesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin-api',
            password='StrongPass123',
        )
        self.student = User.objects.create_user(
            username='student-api',
            password='StrongPass123',
        )
        self.inactive = User.objects.create_user(
            username='inactive-api',
            password='StrongPass123',
            is_active=False,
        )
        self.admin_group = Group.objects.get(name='Administrador')
        self.student_group = Group.objects.get(name='Estudiante')
        self.admin.groups.add(self.admin_group)
        self.student.groups.add(self.student_group)

    def authenticate(self, username, password='StrongPass123'):
        response = self.client.post(
            '/api/auth/token/',
            {'username': username, 'password': password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        return response.data

    def test_login_returns_roles_and_me_requires_token(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)

        data = self.authenticate('student-api')
        self.assertEqual(data['user']['roles'], ['Estudiante'])
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'student-api')

    def test_inactive_user_cannot_login(self):
        response = self.client.post(
            '/api/auth/token/',
            {'username': 'inactive-api', 'password': 'StrongPass123'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_admin_can_create_user_and_student_cannot(self):
        self.authenticate('admin-api')
        response = self.client.post(
            '/api/users/',
            {
                'username': 'created-api',
                'password': 'StrongPass123',
                'email': 'created@example.com',
                'roles': ['Estudiante'],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['roles'], ['Estudiante'])

        self.client.credentials()
        self.authenticate('student-api')
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 403)

    def test_logout_blacklists_refresh_token(self):
        data = self.authenticate('student-api')
        self.client.post(
            '/api/auth/logout/',
            {'refresh': data['refresh']},
            format='json',
        )
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': data['refresh']},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_access_token_immediately(self):
        data = self.authenticate('student-api')
        self.client.post(
            '/api/auth/logout/',
            {'refresh': data['refresh']},
            format='json',
        )
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)

    def test_deactivating_user_revokes_existing_access_token(self):
        data = self.authenticate('student-api')
        self.student.is_active = False
        self.student.save(update_fields=('is_active',))
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {data['access']}",
        )
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)

    def test_admin_can_create_custom_role_with_selected_permission(self):
        self.authenticate('admin-api')
        permission = Permission.objects.get(codename='configure_quizzes')
        response = self.client.post(
            '/api/roles/',
            {
                'name': 'Docente Evaluador',
                'permissions': [permission.pk],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Docente Evaluador')
        self.assertEqual(response.data['permissions'], [permission.pk])
        role = response.data['id']
        response = self.client.patch(
            f'/api/roles/{role}/',
            {'activo': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['activo'])


class QuizAttemptAndRulesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username='student-quiz',
            password='StrongPass123',
        )
        self.student.groups.add(Group.objects.get(name='Estudiante'))
        self.admin = User.objects.create_user(
            username='admin-quiz',
            password='StrongPass123',
        )
        self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.category = Categoria.objects.create(nombre='Matemáticas')
        self.competency = Competencia.objects.create(nombre='Razonamiento')
        self.question = Pregunta.objects.create(
            categoria=self.category,
            competencia=self.competency,
            texto_base='Contexto',
            enunciado='¿Cuánto es dos más dos?',
            retroalimentacion='La suma es cuatro.',
            puntaje=Decimal('1.50'),
        )
        self.correct = OpcionRespuesta.objects.create(
            pregunta=self.question,
            texto='4',
            es_correcta=True,
            orden=1,
        )
        OpcionRespuesta.objects.create(
            pregunta=self.question,
            texto='5',
            orden=2,
        )
        now = timezone.now()
        self.quiz = Cuestionario.objects.create(
            nombre='Cuestionario de prueba',
            fecha_apertura=now - timedelta(minutes=5),
            fecha_cierre=now + timedelta(minutes=30),
            duracion_minutos=10,
            max_intentos=1,
            nota_maxima=Decimal('5.00'),
            nota_aprobar=Decimal('1.00'),
        )
        CuestionarioPregunta.objects.create(
            cuestionario=self.quiz,
            pregunta=self.question,
        )

    def authenticate(self, user, password='StrongPass123'):
        response = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
        )

    def test_attempt_preserves_unanswered_and_calculates_decimal_grade(self):
        self.authenticate(self.student)
        response = self.client.post(
            f'/api/cuestionarios/{self.quiz.id}/iniciar/',
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        attempt_id = response.data['intento_id']

        detail = self.client.get(f'/api/intentos/{attempt_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['respuestas'][0]['opcion'], None)

        response = self.client.patch(
            f'/api/intentos/{attempt_id}/respuestas/',
            {'pregunta': self.question.id, 'opcion': self.correct.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            f'/api/intentos/{attempt_id}/enviar/',
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['puntaje'], '5.00')
        self.assertTrue(response.data['aprobado'])

        revision = self.client.get(f'/api/intentos/{attempt_id}/revision/')
        self.assertEqual(revision.status_code, 200)
        self.assertEqual(revision.data[0]['opcion_correcta'], self.correct.id)

    def test_question_rejects_more_than_one_correct_option(self):
        self.authenticate(self.admin)
        response = self.client.post(
            '/api/preguntas/',
            {
                'categoria': self.category.id,
                'competencia': self.competency.id,
                'enunciado': 'Otra pregunta',
                'tipo': 'UNICA',
                'puntaje': '1.00',
                'opciones': [
                    {'texto': 'A', 'es_correcta': True, 'orden': 1},
                    {'texto': 'B', 'es_correcta': True, 'orden': 2},
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_quiz_rejects_invalid_passing_grade(self):
        serializer_data = {
            'nombre': 'Inválido',
            'fecha_apertura': timezone.now(),
            'fecha_cierre': timezone.now() + timedelta(hours=1),
            'nota_maxima': '5.00',
            'nota_aprobar': '6.00',
            'max_intentos': 1,
        }
        self.authenticate(self.admin)
        response = self.client.post(
            '/api/cuestionarios/',
            serializer_data,
            format='json',
        )
        self.assertEqual(response.status_code, 400)


class ReportesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='report-admin',
            password='StrongPass123',
        )
        self.student = User.objects.create_user(
            username='report-student',
            password='StrongPass123',
            first_name='Ana',
            last_name='Pérez',
        )
        self.other_student = User.objects.create_user(
            username='report-other',
            password='StrongPass123',
            first_name='Luis',
            last_name='Díaz',
        )
        self.no_permission = User.objects.create_user(
            username='report-no-permission',
            password='StrongPass123',
        )
        admin_group = Group.objects.get(name='Administrador')
        student_group = Group.objects.get(name='Estudiante')
        admin_group.permissions.add(
            Permission.objects.get(codename='ver_identificacion_estudiante'),
        )
        self.admin.groups.add(admin_group)
        self.student.groups.add(student_group)
        self.other_student.groups.add(student_group)
        self.period = PeriodoAcademico.objects.create(
            anio=2026,
            nombre='2026-1',
        )
        self.other_period = PeriodoAcademico.objects.create(
            anio=2025,
            nombre='2025-2',
        )
        self.course = CursoGrupo.objects.create(
            nombre='Grupo A',
            periodo=self.period,
        )
        self.other_course = CursoGrupo.objects.create(
            nombre='Grupo B',
            periodo=self.other_period,
        )
        Matricula.objects.create(
            estudiante=self.student,
            curso=self.course,
            identificacion='ID-001',
        )
        Matricula.objects.create(
            estudiante=self.other_student,
            curso=self.course,
            identificacion='ID-002',
        )
        self.category = Categoria.objects.create(nombre='Reporte categoría')
        self.axis = Competencia.objects.create(nombre='Lectura crítica')
        self.quiz = Cuestionario.objects.create(
            nombre='Reporte simulacro',
            curso=self.course,
            nota_maxima=Decimal('5.00'),
            nota_aprobar=Decimal('3.00'),
        )
        self.other_quiz = Cuestionario.objects.create(
            nombre='Otro curso',
            curso=self.other_course,
            nota_maxima=Decimal('5.00'),
            nota_aprobar=Decimal('3.00'),
        )
        self.question = self.create_question(
            'Pregunta reporte',
            self.axis,
        )
        self.other_question = self.create_question(
            'Pregunta otro curso',
            self.axis,
        )
        for quiz, question in (
            (self.quiz, self.question),
            (self.other_quiz, self.other_question),
        ):
            CuestionarioPregunta.objects.create(
                cuestionario=quiz,
                pregunta=question,
            )
        self.correct = self.question.opciones.get(es_correcta=True)
        self.incorrect = self.question.opciones.get(es_correcta=False)
        self.completed_one = self.create_attempt(
            self.student,
            self.quiz,
            Decimal('4.00'),
            self.correct,
        )
        self.completed_two = self.create_attempt(
            self.other_student,
            self.quiz,
            Decimal('2.00'),
            self.incorrect,
        )
        self.create_attempt(
            self.other_student,
            self.other_quiz,
            Decimal('5.00'),
            self.other_question.opciones.get(es_correcta=True),
        )
        self.in_progress = Intento.objects.create(
            usuario=self.student,
            cuestionario=self.quiz,
            curso=self.course,
            periodo=self.period,
        )
        RespuestaIntento.objects.create(
            intento=self.in_progress,
            pregunta=self.question,
            opcion=self.correct,
        )

    def create_question(self, text, axis):
        question = Pregunta.objects.create(
            categoria=self.category,
            competencia=axis,
            enunciado=text,
        )
        OpcionRespuesta.objects.create(
            pregunta=question,
            texto=f'{text} correcta',
            es_correcta=True,
        )
        OpcionRespuesta.objects.create(
            pregunta=question,
            texto=f'{text} incorrecta',
            es_correcta=False,
        )
        return question

    def create_attempt(self, user, quiz, grade, option):
        attempt = Intento.objects.create(
            usuario=user,
            cuestionario=quiz,
            curso=quiz.curso,
            periodo=quiz.curso.periodo,
            puntaje=grade,
            enviado=True,
            estado=Intento.ESTADO_ENVIADO,
            fecha_envio=timezone.now(),
        )
        RespuestaIntento.objects.create(
            intento=attempt,
            pregunta=quiz.cuestionario_preguntas.first().pregunta,
            opcion=option,
        )
        return attempt

    def authenticate(self, user):
        response = self.client.post(
            '/api/auth/token/',
            {'username': user.username, 'password': 'StrongPass123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
        )

    def test_cascading_filters_only_return_compatible_values(self):
        self.authenticate(self.admin)
        response = self.client.get('/api/reportes/filtros/?anio=2026')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['periodos'], [{
            'id': self.period.id,
            'nombre': '2026-1',
            'anio': 2026,
        }])
        self.assertEqual(
            [item['nombre'] for item in response.data['cursos']],
            ['Grupo A'],
        )
        response = self.client.get(
            '/api/reportes/filtros/',
            {'periodo': self.period.id, 'curso': self.other_course.id},
        )
        self.assertEqual(response.status_code, 400)

    def test_selected_filter_keeps_compatible_sibling_options(self):
        sibling_course = CursoGrupo.objects.create(
            nombre='Grupo A2',
            periodo=self.period,
        )
        sibling_period = PeriodoAcademico.objects.create(
            anio=2026,
            nombre='2026-2',
        )
        other_period_course = CursoGrupo.objects.create(
            nombre='Grupo C',
            periodo=sibling_period,
        )
        sibling_quiz = Cuestionario.objects.create(
            nombre='Simulacro hermano',
            curso=sibling_course,
            nota_aprobar=Decimal('3.00'),
        )
        other_period_quiz = Cuestionario.objects.create(
            nombre='Simulacro otro período',
            curso=other_period_course,
            nota_aprobar=Decimal('3.00'),
        )
        for quiz in (sibling_quiz, other_period_quiz):
            CuestionarioPregunta.objects.create(
                cuestionario=quiz,
                pregunta=self.question,
            )
        self.create_attempt(
            self.other_student,
            sibling_quiz,
            Decimal('3.00'),
            self.correct,
        )
        self.create_attempt(
            self.other_student,
            other_period_quiz,
            Decimal('3.00'),
            self.correct,
        )

        self.authenticate(self.admin)
        response = self.client.get(
            '/api/reportes/filtros/',
            {
                'anio': 2026,
                'periodo': self.period.id,
                'curso': self.course.id,
                'eje': self.axis.id,
                'estudiante': self.student.id,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['nombre'] for item in response.data['periodos']},
            {'2026-1', '2026-2'},
        )
        self.assertEqual(
            {item['nombre'] for item in response.data['cursos']},
            {'Grupo A', 'Grupo A2'},
        )
        self.assertEqual(
            {item['id'] for item in response.data['estudiantes']},
            {self.student.id, self.other_student.id},
        )

    def test_indicators_exclude_unfinished_attempt_and_use_quiz_threshold(self):
        self.authenticate(self.admin)
        response = self.client.get(
            '/api/reportes/consultas/',
            {'tipo': 'consolidado', 'curso': self.course.id},
        )
        self.assertEqual(response.status_code, 200)
        metrics = response.data['indicadores']
        self.assertEqual(metrics['estudiantes_distintos'], 2)
        self.assertEqual(metrics['intentos_finalizados'], 2)
        self.assertEqual(metrics['promedio'], Decimal('3'))
        self.assertEqual(metrics['minima'], Decimal('2'))
        self.assertEqual(metrics['maxima'], Decimal('4'))
        self.assertEqual(metrics['aprobados'], 1)
        self.assertEqual(metrics['no_aprobados'], 1)
        self.assertEqual(metrics['porcentaje_aprobacion'], 50)
        self.assertEqual(metrics['umbrales_aprobacion'], ['3.00'])
        self.assertEqual(response.data['count'], 3)

    def test_search_and_sorting(self):
        self.authenticate(self.admin)
        response = self.client.get(
            '/api/reportes/',
            {
                'tipo': 'consolidado',
                'curso': self.course.id,
                'buscar': 'Pérez',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(all(
            row['estudiante'] == 'Ana Pérez'
            for row in response.data['results']
        ))
        response = self.client.get(
            '/api/reportes/',
            {
                'tipo': 'consolidado',
                'curso': self.course.id,
                'ordenar': 'calificacion',
                'direccion': 'desc',
            },
        )
        self.assertEqual(
            [row['calificacion'] for row in response.data['results']],
            [Decimal('4.00'), Decimal('2.00'), None],
        )

    def test_pagination_preserves_active_filters(self):
        for index in range(12):
            self.create_attempt(
                self.student,
                self.quiz,
                Decimal('4.00'),
                self.correct,
            )
        self.authenticate(self.admin)
        response = self.client.get(
            '/api/reportes/',
            {'curso': self.course.id, 'pagina': 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(len(response.data['results']), 5)
        self.assertIn(f'curso={self.course.id}', response.data['previous'])

    def test_individual_history_never_mixes_students(self):
        self.authenticate(self.admin)
        response = self.client.get(
            f'/api/reportes/historial/{self.student.id}/',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(
            item['usuario__username'] == self.student.username
            for item in response.data
        ))
        self.assertEqual(
            sum(item['estado'] == Intento.ESTADO_EN_CURSO for item in response.data),
            1,
        )
        self.authenticate(self.student)
        response = self.client.get(
            f'/api/reportes/historial/{self.other_student.id}/',
        )
        self.assertEqual(response.status_code, 404)

    def test_excel_matches_consolidated_query(self):
        for _ in range(10):
            self.create_attempt(
                self.student,
                self.quiz,
                Decimal('4.00'),
                self.correct,
            )
        self.authenticate(self.admin)
        params = {
            'tipo': 'consolidado',
            'curso': self.course.id,
            'ordenar': 'fecha',
            'direccion': 'asc',
        }
        query = self.client.get('/api/reportes/consultas/', params)
        all_results = list(query.data['results'])
        for page_number in range(2, (query.data['count'] + 9) // 10 + 1):
            page_response = self.client.get(
                '/api/reportes/consultas/',
                {**params, 'pagina': page_number},
            )
            self.assertEqual(page_response.status_code, 200)
            all_results.extend(page_response.data['results'])

        export = self.client.get(
            f'/api/reportes/exportar/consolidado/?curso={self.course.id}'
            '&ordenar=fecha&direccion=asc',
        )
        self.assertEqual(export.status_code, 200)
        workbook = load_workbook(
            BytesIO(b''.join(export.streaming_content)),
            data_only=True,
        )
        sheet = workbook['Consolidado general']
        self.assertEqual(sheet.max_row, len(all_results) + 7)
        self.assertEqual(len(all_results), query.data['count'])
        for offset, result in enumerate(all_results, start=8):
            self.assertEqual(sheet.cell(offset, 1).value, result['anio'])
            self.assertEqual(sheet.cell(offset, 2).value, result['periodo'])
            self.assertEqual(sheet.cell(offset, 3).value, result['curso'])
            self.assertEqual(sheet.cell(offset, 4).value, result['estudiante'])
            self.assertEqual(
                sheet.cell(offset, 5).value,
                result.get('identificacion', ''),
            )
            self.assertEqual(sheet.cell(offset, 6).value, result['simulacro'])
            result_date = result['fecha']
            if isinstance(result_date, str):
                result_date = datetime.fromisoformat(result_date)
            if timezone.is_aware(result_date):
                result_date = timezone.localtime(result_date).replace(tzinfo=None)
            result_date = result_date.replace(
                microsecond=(result_date.microsecond // 1000) * 1000,
            )
            self.assertEqual(sheet.cell(offset, 7).value, result_date)
            if result['calificacion'] is not None:
                self.assertEqual(
                    sheet.cell(offset, 8).value,
                    float(result['calificacion']),
                )
            else:
                self.assertIsNone(sheet.cell(offset, 8).value)
            self.assertEqual(sheet.cell(offset, 9).value, result['estado'])
            self.assertEqual(
                sheet.cell(offset, 10).value,
                float(result['nota_aprobar']),
            )
        self.assertEqual(
            workbook['Promedio por estudiante'].cell(9, 1).value,
            'Ana Pérez',
        )

    def test_excel_with_no_results_still_returns_headers(self):
        self.authenticate(self.admin)
        response = self.client.get(
            '/api/reportes/exportar/consolidado/?anio=2024',
        )
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(
            BytesIO(b''.join(response.streaming_content)),
            data_only=True,
        )
        sheet = workbook['Consolidado general']
        self.assertEqual(sheet.cell(7, 1).value, 'Año')
        self.assertEqual(sheet.cell(8, 1).value, 'Sin resultados')

    def test_authentication_permission_and_student_scope(self):
        response = self.client.get('/api/reportes/')
        self.assertEqual(response.status_code, 401)
        self.authenticate(self.no_permission)
        response = self.client.get('/api/reportes/')
        self.assertEqual(response.status_code, 403)
        self.authenticate(self.student)
        response = self.client.get('/api/reportes/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(
            row['estudiante_id'] == self.student.id
            for row in response.data['results']
        ))
        self.assertTrue(all(
            'identificacion' not in row
            for row in response.data['results']
        ))
        response = self.client.get(
            '/api/reportes/',
            {'estudiante': self.other_student.id},
        )
        self.assertEqual(response.status_code, 404)

    def test_axis_report_counts_answered_rows_only_and_keeps_grade_null(self):
        self.authenticate(self.admin)
        response = self.client.get(
            '/api/reportes/',
            {'tipo': 'ejes', 'curso': self.course.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        row = response.data['results'][0]
        self.assertEqual(row['respuestas_registradas'], 3)
        self.assertEqual(row['aciertos'], 2)
        self.assertEqual(row['errores'], 1)
        self.assertEqual(row['nota_promedio'], None)

    def test_excel_export_is_a_valid_workbook(self):
        self.authenticate(self.admin)
        response = self.client.get(
            f'/api/reportes/exportar/ejes/?curso={self.course.id}',
        )
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(
            BytesIO(b''.join(response.streaming_content)),
            data_only=True,
        )
        self.assertIn('Desempeño por eje', workbook.sheetnames)
        self.assertEqual(
            workbook['Desempeño por eje'].cell(7, 4).value,
            'Eje',
        )
