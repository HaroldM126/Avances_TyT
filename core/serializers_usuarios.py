import re
from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework import serializers

from .models import CursoGrupo, Matricula, PerfilUsuario, Rol
from django.contrib.auth.password_validation import validate_password


NAME_PATTERN = re.compile(
    r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$",
    re.UNICODE,
)
IDENTITY_PATTERN = re.compile(r'^\d{6,12}$')


def validate_person_name(value, field_name):
    value = ' '.join(value.strip().split())
    if not value or not NAME_PATTERN.fullmatch(value):
        raise serializers.ValidationError(
            f'{field_name} solo puede contener letras y espacios.',
        )
    return value


class BaseInstitutionalUserSerializer(serializers.Serializer):
    nombres = serializers.CharField(max_length=150)
    apellidos = serializers.CharField(max_length=150)
    numero_identidad = serializers.CharField(max_length=20)
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

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'username': instance.username,
            'nombres': instance.first_name,
            'apellidos': instance.last_name,
            'numero_identidad': instance.perfil.numero_identidad,
            'rol': instance.groups.values_list('name', flat=True).first(),
        }

    def validate_nombres(self, value):
        return validate_person_name(value, 'Los nombres')

    def validate_apellidos(self, value):
        return validate_person_name(value, 'Los apellidos')

    def validate_numero_identidad(self, value):
        value = value.strip()
        if not IDENTITY_PATTERN.fullmatch(value):
            raise serializers.ValidationError(
                'La cédula debe contener únicamente entre 6 y 12 números.',
            )
        if PerfilUsuario.objects.filter(numero_identidad=value).exists():
            raise serializers.ValidationError(
                'La cédula ya está registrada.',
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'La cédula ya está asociada a un usuario.',
            )
        return value

    def validate(self, data):
        if data['password'] != data['password_confirmation']:
            raise serializers.ValidationError({
                'password_confirmation': 'Las contraseñas no coinciden.',
            })
        user = User(
            username=data['numero_identidad'],
            first_name=data['nombres'],
            last_name=data['apellidos'],
        )
        validate_password(data['password'], user)
        return data

    def create_user(self, validated_data, role_name):
        password = validated_data.pop('password')
        validated_data.pop('password_confirmation')
        identity = validated_data.pop('numero_identidad')
        group, _ = Group.objects.get_or_create(name=role_name)
        Rol.objects.get_or_create(grupo=group)
        user = User(
            username=identity,
            first_name=validated_data.pop('nombres'),
            last_name=validated_data.pop('apellidos'),
        )
        user.set_password(password)
        user.save()
        PerfilUsuario.objects.create(
            usuario=user,
            numero_identidad=identity,
        )
        user.groups.add(group)
        return user


class EstudianteRegistroSerializer(BaseInstitutionalUserSerializer):
    curso = serializers.PrimaryKeyRelatedField(
        queryset=CursoGrupo.objects.select_related('periodo').all(),
    )

    @transaction.atomic
    def create(self, validated_data):
        course = validated_data.pop('curso')
        user = self.create_user(validated_data, 'Estudiante')
        Matricula.objects.create(
            estudiante=user,
            curso=course,
            identificacion=user.perfil.numero_identidad,
        )
        return user


class DocenteRegistroSerializer(BaseInstitutionalUserSerializer):
    @transaction.atomic
    def create(self, validated_data):
        return self.create_user(validated_data, 'Docente')
