from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from rest_framework.test import APIClient


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
