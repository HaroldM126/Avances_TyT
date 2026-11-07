from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone
from rest_framework_simplejwt.tokens import UntypedToken
from uuid import uuid4
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Rol, SesionJWT


class AuthTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['session_id'] = str(uuid4())
        token['roles'] = list(
            user.groups.filter(rol__activo=True).values_list('name', flat=True)
        )
        token['is_staff'] = user.is_staff
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        refresh_claims = UntypedToken(data['refresh'])
        session_id = refresh_claims['session_id']
        for token_key in ('access', 'refresh'):
            token = UntypedToken(data[token_key])
            SesionJWT.objects.create(
                sesion_id=session_id,
                jti=token['jti'],
                usuario=self.user,
                expira_en=datetime.fromtimestamp(
                    token['exp'],
                    tz=datetime_timezone.utc,
                ),
            )
        data['user'] = UserSerializer(self.user).data
        return data


class InitialAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'password_confirmation',
        )
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError(
                'El nombre de usuario es obligatorio.',
            )
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta con este nombre de usuario.',
            )
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta con este correo electrónico.',
            )
        return email

    def validate(self, data):
        if data['password'] != data['password_confirmation']:
            raise serializers.ValidationError({
                'password_confirmation': 'Las contraseñas no coinciden.',
            })
        candidate = User(
            username=data.get('username', ''),
            email=data.get('email', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )
        validate_password(data['password'], candidate)
        return data

    @transaction.atomic
    def create(self, validated_data):
        if User.objects.filter(is_superuser=True).exists():
            raise serializers.ValidationError({
                'detail': 'La configuración del administrador inicial ya fue completada.',
            })
        validated_data.pop('password_confirmation')
        password = validated_data.pop('password')
        user = User(is_staff=True, is_superuser=True, **validated_data)
        user.set_password(password)
        user.save()
        return user


class PermissionSerializer(serializers.ModelSerializer):
    PERMISSION_LABELS = {
        'add_cuestionario': 'Crear cuestionarios',
        'change_cuestionario': 'Editar cuestionarios',
        'delete_cuestionario': 'Eliminar cuestionarios',
        'view_cuestionario': 'Consultar cuestionarios',
        'manage_users': 'Administrar usuarios',
        'manage_roles': 'Administrar roles y permisos',
        'manage_question_bank': 'Administrar banco de preguntas',
        'configure_quizzes': 'Configurar cuestionarios',
        'view_results': 'Consultar resultados',
        'ver_reportes': 'Consultar reportes académicos',
        'ver_identificacion_estudiante': 'Consultar identificaciones de estudiantes',
    }

    name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'content_type')
        read_only_fields = fields

    def get_name(self, obj):
        return self.PERMISSION_LABELS.get(obj.codename, obj.name)


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    activo = serializers.BooleanField(required=False)
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.filter(
            content_type__app_label='core',
            content_type__model='cuestionario',
        ),
        required=False,
    )

    def to_representation(self, instance):
        return {
            'id': instance.pk,
            'name': instance.grupo.name,
            'activo': instance.activo,
            'permissions': list(
                instance.grupo.permissions.values_list('pk', flat=True)
            ),
        }

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        group = Group.objects.create(name=validated_data.pop('name'))
        role = Rol.objects.create(grupo=group, **validated_data)
        group.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        if 'name' in validated_data:
            instance.grupo.name = validated_data.pop('name')
            instance.grupo.save(update_fields=('name',))
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if permissions is not None:
            instance.grupo.permissions.set(permissions)
        return instance


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(
        many=True,
        source='groups',
        slug_field='name',
        queryset=Group.objects.all(),
        required=False,
    )
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    permissions = serializers.SerializerMethodField(read_only=True)
    numero_identidad = serializers.SerializerMethodField(read_only=True)
    cursos = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'roles', 'password',
            'permissions', 'numero_identidad', 'cursos',
        )
        read_only_fields = ('id', 'is_staff')

    def get_permissions(self, obj):
        if obj.is_superuser:
            return ['*']
        return list(
            obj.groups.filter(rol__activo=True)
            .values_list('permissions__codename', flat=True)
            .distinct()
        )

    def get_numero_identidad(self, obj):
        return getattr(getattr(obj, 'perfil', None), 'numero_identidad', '')

    def get_cursos(self, obj):
        return list(
            obj.matriculas.filter(activa=True).values_list(
                'curso__nombre',
                flat=True,
            ),
        )

    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError(
                {'password': 'La contraseña es obligatoria.'}
            )
        inactive = [group.name for group in groups if not group.rol.activo]
        if inactive:
            raise serializers.ValidationError(
                {'roles': f'Los roles inactivos no se pueden asignar: {inactive}.'}
            )
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        groups = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            inactive = [group.name for group in groups if not group.rol.activo]
            if inactive:
                raise serializers.ValidationError(
                    {'roles': f'Los roles inactivos no se pueden asignar: {inactive}.'}
                )
            instance.groups.set(groups)
        return instance
