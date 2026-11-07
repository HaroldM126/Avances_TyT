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

Configuración del administrador inicial

Para crear el primer superusuario desde la pantalla de acceso, configura
`INITIAL_ADMIN_SETUP_TOKEN` en el entorno antes de iniciar Django. El formulario
requiere ese token, valida la contraseña y solo funciona mientras no exista
ningún superusuario. Después de crear el administrador, la operación queda
bloqueada; los estudiantes, docentes y demás usuarios deben ser creados desde
la administración autenticada.

Autenticación y roles

- `POST /api/auth/token/`: inicia sesión y devuelve tokens `access` y `refresh`.
- `POST /api/auth/token/refresh/`: renueva el token de acceso.
- `POST /api/auth/logout/`: invalida el refresh token enviado.
- `GET /api/auth/me/`: consulta el usuario autenticado, sus roles y permisos.
- El perfil de la barra superior muestra nombres, apellidos, cédula y correo;
  desde allí se cambia la contraseña y se cierra sesión. Las contraseñas
  requieren mínimo 8 caracteres, al menos una letra y un número.
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

Registro institucional

Los usuarios con permiso `manage_users` pueden registrar estudiantes y docentes
desde Gestión. El registro de estudiantes exige curso/grupo y crea la matrícula;
el registro de docentes no solicita curso. En ambos casos la cédula es numérica,
única y se usa como nombre de usuario, los nombres y apellidos solo aceptan
caracteres alfabéticos, y el rol se asigna automáticamente en el servidor.

Cuestionarios e intentos

Los cuestionarios admiten fechas de apertura y cierre, tiempo límite,
intentos permitidos, calificación máxima, nota para aprobar y configuración
de revisión. Los estudiantes solo reciben cuestionarios de sus matrículas;
el servidor bloquea los que estén fuera de horario o hayan agotado sus
intentos. Al iniciar un intento se crea una respuesta persistente para cada
pregunta; una respuesta sin opción representa una pregunta sin responder y
puede marcarse para revisión. El intento se cierra al llegar el primero entre
la hora de cierre y el tiempo límite, conservando las respuestas guardadas.
La calificación se calcula con `Decimal` y se expone como `puntaje` y
`calificacion_final`.

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

Consultas y reportes
--------------------

El módulo administrativo de reportes ofrece siete consultas: consolidado,
resultados por período, resultados por curso, desempeño por eje, calificaciones
por estudiante, historial individual y preguntas de mayor dificultad.

Los endpoints requieren autenticación. `Administrador` recibe `ver_reportes`
por defecto; a otros roles docentes se les asigna desde la administración de
roles. Los estudiantes pueden consultar únicamente sus propios intentos. El
campo de identificación se devuelve o exporta solo a usuarios con el permiso
independiente `ver_identificacion_estudiante`.

- `GET /api/reportes/filtros/`: opciones encadenadas para `anio`, `periodo`,
  `curso`, `eje` y `estudiante`; admite `buscar`.
- `GET /api/reportes/` y `GET /api/reportes/consultas/`: consulta paginada
  (10 registros) con `tipo`, filtros, `buscar`, `ordenar`, `direccion` y
  `pagina`. Los tipos son `consolidado`, `periodos`, `cursos`, `ejes`,
  `calificaciones`, `historial` y `dificultad`.
- `GET /api/reportes/historial/{estudiante_id}/`: historial cronológico de un
  estudiante, sin incluir intentos de otras personas.
- `GET /api/reportes/exportar/{tipo}/`: descarga completa en Excel para
  `consolidado`, `ejes` o `historial`, aplicando los mismos filtros y permisos.
- `GET /api/cursos-academicos/`: cursos disponibles para asignar a un
  cuestionario; requiere permiso para configurar cuestionarios.

Para reportar por período, curso o grupo, crea los períodos y cursos en el
admin de Django, registra las matrículas y asigna un curso al cuestionario. El
curso y período se copian al nuevo intento al iniciarlo. Los intentos históricos
mantienen `curso = NULL` y `periodo = NULL`; no se infiere ni cambia
retroactivamente su clasificación.
Cada curso pertenece a un período y cada matrícula enlaza a un estudiante con
un curso.

La nota mínima de aprobación continúa siendo `Cuestionario.nota_aprobar` y
puede variar por cuestionario. Promedio, nota mínima/máxima y porcentaje de
aprobación consideran únicamente intentos enviados con nota. El historial puede
mostrar intentos en curso, pero estos no se incluyen en esas métricas. La nota
promedio por eje no se calcula porque el dominio no define una regla para ello.

Para poblar datos de demostración:

```powershell
$env:DJANGO_USE_SQLITE = '1'
python manage.py migrate
python manage.py seed_reportes
```

Consulta [docs/ESQUEMA_MODELOS.md](docs/ESQUEMA_MODELOS.md) para el modelo de
datos y [docs/EVIDENCIAS.md](docs/EVIDENCIAS.md) para decisiones y una guía de
demostración.