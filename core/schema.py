from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SessionJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'core.authentication.SessionJWTAuthentication'
    name = 'BearerAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': (
                'Token JWT obtenido en POST /api/auth/token/. '
                'Ejemplo: Bearer <access_token>'
            ),
        }
