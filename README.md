Simulador TyT
Base de datos
Entidades
Categoria
Pregunta
OpcionRespuesta
Cuestionario
CuestionarioPregunta
Intento
RespuestaIntento
Tecnologías
Django 5.2
MySQL
Django REST Framework
SimpleJWT

Configuración local

La aplicación usa MySQL por defecto. Configura `MYSQL_DATABASE`, `MYSQL_USER`,
`MYSQL_PASSWORD`, `MYSQL_HOST` y `MYSQL_PORT`. También define
`DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`; para pruebas locales sin MySQL
puedes usar `DJANGO_USE_SQLITE=1`.

Autenticación y roles

- `POST /api/auth/token/`: inicia sesión y devuelve tokens `access` y `refresh`.
- `POST /api/auth/token/refresh/`: renueva el token de acceso.
- `POST /api/auth/logout/`: invalida el refresh token enviado.
- `GET /api/auth/me/`: consulta el usuario autenticado, sus roles y permisos.
- `/api/users/`: administración de usuarios, disponible para quienes tienen `core.manage_users`.
- `/api/roles/`: administración de roles personalizados y permisos, disponible para quienes tienen `core.manage_roles`.

Los roles se representan con grupos de Django. La migración crea permisos de
funcionalidad para que un administrador pueda asignarlos individualmente a
`Administrador`, `Estudiante` o a cualquier rol personalizado. Todas las
restricciones se validan en el servidor, no solo en la interfaz. Cada rol
también tiene el campo `activo`; los roles desactivados no pueden asignarse ni
conceden permisos aunque el usuario conserve el grupo.