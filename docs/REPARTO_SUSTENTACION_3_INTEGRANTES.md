# Reparto de sustentación presencial (3 integrantes)

**Fecha:** Sábado 28 de noviembre de 2026, 9:00 a. m.  
**Duración sugerida:** 12 a 15 minutos totales (4–5 minutos por integrante) + espacio para preguntas del docente.

---

## Integrante 1 (Ana Zuñiga): Arquitectura, Base de Datos en la Nube y Despliegue (Actividades 2 y 3)

### Responsabilidades en la exposición
1. **Contexto del proyecto y repositorio GitHub:** mostrar la estructura (`config/`, `core/`, `frontend/`, `requirements.txt`, `.gitignore` excluyendo `.env`, `.venv`, backups `.sql`).
2. **Base de datos MariaDB/MySQL en la nube:**
   - Explicar qué proveedor se utilizó, cómo se conservó el motor MariaDB/MySQL (`django.db.backends.mysql` + `PyMySQL` + TLS) sin migrar a PostgreSQL/Supabase.
   - Explicar las variables de entorno (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSL_MODE`).
3. **Despliegue en Vercel y configuración de producción:**
   - Mostrar `vercel.json`, `api/index.py`, `build_files.sh`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `WhiteNoise` y `HTTPS`.
4. **Demostración en vivo (parte 1):**
   - Abrir la URL pública desde el navegador y mostrar `GET /api/health/` (`SELECT 1` -> `database: ok`, `engine: mysql`).
   - Iniciar sesión con cuenta **Administrador** y **Estudiante** para mostrar separación de roles y permisos (`auth/me/`, menú de Gestión vs vista de Estudiante).

### Preguntas probables para Integrante 1
- *¿Por qué usan `PyMySQL` en lugar de `mysqlclient`?*  
  Porque `PyMySQL` es puro Python (sin compilación nativa en C) y funciona sin problemas en entornos serverless como Vercel, conectándose al motor `django.db.backends.mysql` mediante `pymysql.install_as_MySQLdb()` en `config/__init__.py`.
- *¿Cómo garantizan la persistencia y seguridad de la BD?*  
  Con conexión remota sobre TLS hacia la instancia cloud (no SQLite efímero) y sin exponer secretos en el repositorio (`.env` ignorado; credenciales cargadas como variables de entorno en Vercel).

---

## Integrante 2 (Harold Meneses): API REST, Swagger / OpenAPI y Pruebas de Autorización (Actividad 1 y parte de Actividad 4)

### Responsabilidades en la exposición
1. **Integración de `drf-spectacular`:**
   - Explicar la configuración en `config/settings.py` (`INSTALLED_APPS`, `DEFAULT_SCHEMA_CLASS`, `SPECTACULAR_SETTINGS`), las rutas `/api/schema/` y `/api/docs/`, y el esquema de seguridad JWT `BearerAuth` (`core/schema.py`).
2. **Explicación de los 6 endpoints mínimos documentados:**
   - `GET /api/simulacros/` (reutiliza `Cuestionario.objects.disponibles()` y matrículas para estudiantes, o listado configurado para docentes/admin).
   - `GET /api/preguntas/` y `PATCH /api/preguntas/{id}/` (protegidos por `PuedeGestionarPreguntas` / `manage_question_bank`).
   - `POST /api/intentos/` (inicia intento validando rol estudiante, vigencia, límite de intentos y contraseña en `core/services/intentos.py`).
   - `GET /api/resultados/` (filtra según rol y respeta `publicar_resultado`).
   - `GET /api/reportes/` (filtros jerárquicos por año, período, curso y eje temático).
3. **Demostración en vivo en Swagger (`/api/docs/`):**
   - Autenticarse con `POST /api/auth/token/` y pegar el token en **Authorize**.
   - Probar con **Try it out** un `GET` real (ej. `/api/simulacros/` o `/api/preguntas/`) y un `POST` real (ej. `/api/intentos/` o `/api/preguntas/`), mostrando que el cambio queda guardado en Django y en MariaDB remota.
   - Probar un **acceso no autorizado** (`401` sin token y `403` intentando `PATCH /api/preguntas/{id}/` o `GET /api/preguntas/` con token de estudiante).

### Preguntas probables para Integrante 2
- *¿Cómo documentan autenticación y permisos en Swagger?*  
  Con `OpenApiAuthenticationExtension` en `core/schema.py` para `SessionJWTAuthentication` y decoradores `@extend_schema` / `@extend_schema_view` que documentan parámetros, cuerpos, respuestas y códigos `200/201/400/401/403/404`.
- *¿Cómo evitan duplicar lógica entre endpoints existentes y Swagger?*  
  La lógica de inicio de intento se centralizó en `iniciar_intento_para_usuario()` (`core/services/intentos.py`), reutilizada tanto por `POST /api/cuestionarios/{id}/iniciar/` como por `POST /api/intentos/`.

---

## Integrante 3 (Jamilton Legarda): Flujo Funcional Integral, Calificación, Reportes y Persistencia en MariaDB (Actividad 4)

### Responsabilidades en la exposición
1. **CRUD y persistencia en MariaDB remota:**
   - Crear una pregunta manualmente desde Django (panel de Gestión o `/admin/`), editarla y mostrar ambos cambios reflejados en la base MariaDB remota (usando cliente gráfico como DBeaver/HeidiSQL/MySQL Workbench o consola).
   - Eliminar un registro de prueba no relacionado (por ejemplo, una categoría de prueba creada para la demo) y verificar en MariaDB que fue eliminado.
2. **Simulacro completo como estudiante:**
   - Iniciar sesión como estudiante (`demo_estudiante_1` o estudiante de prueba).
   - Abrir un simulacro asignado, mostrar el **temporizador** en pantalla, responder las preguntas (mostrando guardado automático `PATCH /api/intentos/{id}/respuestas/`), finalizar (`POST /api/intentos/{id}/enviar/`).
   - Explicar cómo `Intento.calcular_puntaje()` calcula la nota con `Decimal` y redondeo `ROUND_HALF_UP`: `(puntaje_correcto / puntaje_total) * nota_maxima`.
3. **Consulta de resultados y filtros:**
   - Iniciar sesión como administrador/docente, ir a **Consultas y reportes**, aplicar filtros por **año**, **curso** y **eje temático**, y contrastar los números mostrados en Django con la consulta directa en MariaDB remota.

### Preguntas probables para Integrante 3
- *¿Cómo se evita alterar resultados históricos si se edita un cuestionario o curso?*  
  Al iniciar un intento, `curso` y `periodo` se copian como FKs del cuestionario en `Intento`, y cada pregunta del simulacro crea una fila en `RespuestaIntento`. Los cálculos toman únicamente intentos finalizados (`enviado=True`, `fecha_envio IS NOT NULL`, `puntaje IS NOT NULL`).
- *¿Cómo se verifica que la base es realmente remota y persistente?*  
  Consultando directamente las tablas (`core_pregunta`, `core_intento`, `core_respuestaintento`) en la instancia cloud con DBeaver/CLI después de operar desde la URL pública de Vercel, y confirmando que los datos permanecen tras un nuevo despliegue.

---

## Checklist rápido antes de entrar a sustentar (8:30 a. m.)

- [ ] Probar la URL pública desde otro equipo o red móvil (datos) para confirmar que no depende de `localhost`.
- [ ] Tener abiertas 4 pestañas listas:
  1. Aplicación publicada (`https://<tu-app>.vercel.app/`)
  2. Swagger UI (`https://<tu-app>.vercel.app/api/docs/`)
  3. Django Admin (`https://<tu-app>.vercel.app/admin/`)
  4. Cliente SQL (DBeaver / HeidiSQL / consola) conectado a la MariaDB remota.
- [ ] Tener a la mano credenciales de prueba (Administrador y Estudiante) y un registro no relacionado listo para eliminar en la demo.
- [ ] Verificar que el informe PDF ya esté subido en Moodle antes de las 9:00 a. m.
