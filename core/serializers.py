from django.contrib.auth.models import Group, Permission, User
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


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'content_type')
        read_only_fields = fields


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

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'roles', 'password',
            'permissions',
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
