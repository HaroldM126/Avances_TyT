from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )
    new_password_confirmation = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('La contraseña actual no es válida.')
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirmation']:
            raise serializers.ValidationError({
                'new_password_confirmation': 'Las contraseñas no coinciden.',
            })
        validate_password(data['new_password'], self.context['request'].user)
        return data
