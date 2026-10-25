from django.contrib.auth.models import Group, Permission, User
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from datetime import timedelta
from decimal import Decimal

from .models import (
    Categoria,
    Competencia,
    Cuestionario,
    CuestionarioPregunta,
    OpcionRespuesta,
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
