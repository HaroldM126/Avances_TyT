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
- `/api/intentos/`: consulta los intentos propios; quienes tienen `core.view_results` pueden consultar todos.
- `PATCH /api/intentos/{id}/respuestas/`: guarda o limpia una respuesta durante un intento.
- `POST /api/intentos/{id}/enviar/`: cierra el intento y calcula la calificación final.
- `GET /api/intentos/{id}/revision/`: consulta la revisión si el cuestionario la permite.
- Las sesiones JWT se registran y se revocan inmediatamente al cerrar sesión o
  desactivar una cuenta.

Los roles se representan con grupos de Django. La migración crea permisos de
funcionalidad para que un administrador pueda asignarlos individualmente a
`Administrador`, `Estudiante` o a cualquier rol personalizado. Todas las
restricciones se validan en el servidor, no solo en la interfaz. Cada rol
también tiene el campo `activo`; los roles desactivados no pueden asignarse ni
conceden permisos aunque el usuario conserve el grupo.

Cuestionarios e intentos

Los cuestionarios admiten fechas de apertura y cierre, tiempo límite,
intentos permitidos, calificación máxima, nota para aprobar y configuración
de revisión. Al iniciar un intento se crea una respuesta persistente para
cada pregunta; una respuesta sin opción representa una pregunta sin
responder. La calificación se calcula con `Decimal` y se expone como
`puntaje` y `calificacion_final`.

Las preguntas incluyen texto base, enunciado, opciones, una única respuesta
correcta, retroalimentación y puntaje. Las filas inválidas de una importación
Excel se almacenan junto con el resultado de la importación antes de permitir
la confirmación.

La importación se realiza en dos fases: `POST
/api/preguntas/importar/preview/` devuelve un `importacion_id` y registra las
filas; `POST /api/preguntas/importar/confirmar/` recibe ese identificador y
confirma únicamente la vista previa persistida. El historial está disponible
en `GET /api/preguntas/importar/`.

Las calificaciones se normalizan a la nota máxima configurada mediante la
relación entre el puntaje obtenido y el puntaje total de las preguntas. El
resultado se redondea a dos decimales usando `Decimal`.