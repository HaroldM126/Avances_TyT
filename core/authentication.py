from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import SesionJWT


class SessionJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, validated_token = result
        if not user.is_active:
            return None
        jti = validated_token.get('jti')
        sesion = SesionJWT.objects.filter(
            jti=jti,
            usuario=user,
            revocada_en__isnull=True,
            expira_en__gt=timezone.now(),
        ).first()
        if sesion is None:
            from rest_framework_simplejwt.exceptions import AuthenticationFailed
            raise AuthenticationFailed('La sesión ya no es válida.')
        return user, validated_token
