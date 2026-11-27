# Guía de despliegue en la nube y verificación del parcial final

Este documento resume la configuración implementada en el repositorio para cumplir las Actividades 1, 2, 3 y 4 del parcial final de **Electiva Profesional III – Frameworks**.

---

## 1. Actividad 1 – API REST y Swagger (`drf-spectacular`)

- **Esquema OpenAPI 3.0:** `GET /api/schema/`
- **Documentación interactiva Swagger UI:** `GET /api/docs/`
- **Autenticación en Swagger:** botón **Authorize** usando `BearerAuth` (JWT obtenido en `POST /api/auth/token/`).
- **Operaciones mínimas documentadas sobre lógica y modelos reales:**
  1. `GET /api/simulacros/` — Listar simulacros disponibles (según rol estudiante o gestor).
  2. `GET /api/preguntas/` — Consultar preguntas autorizadas (`manage_question_bank`, filtros `categoria`, `competencia`, `tipo`, `activa`).
  3. `POST /api/intentos/` — Registrar un intento (validación de rol, fechas, matrícula, límite de intentos y contraseña).
  4. `GET /api/resultados/` — Consultar resultados permitidos según rol y `publicar_resultado`.
  5. `GET /api/reportes/` — Consultar reportes filtrados por `anio`, `periodo`, `curso`, `eje`, `estudiante`, `buscar`, `tipo`, `ordenar`, `direccion`, `pagina`.
  6. `PATCH /api/preguntas/{id}/` — Actualizar una pregunta autorizada.

---

## 2. Actividad 2 – Base de datos MariaDB/MySQL en la nube

### 2.1. Respaldo de base de datos local (solo datos ficticios/demo)

Si trabajaste primero en local con MariaDB/MySQL:

```powershell
# Exportar respaldo SQL (sin datos reales sensibles)
& "C:\Program Files\MariaDB 12.3\bin\mariadb-dump.exe" -h 127.0.0.1 -P 3306 -u root -p parcial_simulador_tyt > respaldo_tyt_demo.sql
```

> **Nota:** No subas archivos `.sql` ni `.env` al repositorio (ya están excluidos en `.gitignore`).

### 2.2. Crear instancia remota MariaDB/MySQL con TLS

Opciones gratuitas compatibles con **MariaDB/MySQL** y conexiones externas TLS (sin migrar a PostgreSQL ni Supabase):

- **Layerbase** (MariaDB Cloud gratuito con protocolo MySQL y TLS obligatorio).
- **TiDB Cloud Serverless** (compatible con protocolo MySQL + TLS, requiere `DB_SSL_MODE=VERIFY_CA` o certificado CA).
- **Railway / Clever Cloud / MariaDB SkySQL (trial)**.

Configura las variables de entorno en `.env` (local) y en Vercel:

| Variable | Descripción |
| --- | --- |
| `DB_NAME` | Nombre de la base de datos remota |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña del usuario |
| `DB_HOST` | Host público del servidor MariaDB/MySQL |
| `DB_PORT` | Puerto remoto (ej. `3306` o `4000`) |
| `DB_SSL_MODE` | `REQUIRED` o `VERIFY_CA` / `VERIFY_IDENTITY` |
| `DB_SSL_CA` | (Opcional) Ruta al certificado `.pem` o contenido PEM del CA |

### 2.3. Migrar tablas y cargar datos de prueba (sin duplicar)

```powershell
# Con las variables DB_* apuntando a la instancia remota en .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py seed_reportes
```

*(Si importas `respaldo_tyt_demo.sql` directamente en una base vacía, ejecuta luego `python manage.py migrate` para verificar que no falten migraciones y evita ejecutar dos veces scripts que inserten registros sin `get_or_create`.)*

### 2.4. Comprobar conexión remota (`SELECT 1`) y persistencia

1. Desde terminal local apuntando a la nube:
   ```powershell
   .\.venv\Scripts\python.exe manage.py shell -c "from django.db import connection; c = connection.cursor(); c.execute('SELECT 1'); print('SELECT 1 =>', c.fetchone())"
   ```
2. Desde la URL pública desplegada:
   - Consultar `GET https://<tu-app>.vercel.app/api/health/` -> debe responder `{"status": "ok", "database": "ok", "engine": "mysql"}`.

---

## 3. Actividad 3 – Despliegue de Django + Frontend en Vercel

El proyecto ya incluye `vercel.json`, `api/index.py`, `build_files.sh`, `whitenoise` y `PyMySQL` (`requirements.txt`).

1. Sube los cambios a GitHub (`main`). Verifica que `.env`, `.venv/`, `db.sqlite3` y `*.sql` **no** estén en el repositorio.
2. En **Vercel**, importa el repositorio de GitHub (`HaroldM126/Avances_TyT`).
3. Configura en **Project Settings → Environment Variables**:
   - `SECRET_KEY` (clave aleatoria segura)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `.vercel.app` (o tu dominio exacto)
   - `CSRF_TRUSTED_ORIGINS` = `https://<tu-proyecto>.vercel.app`
   - `INITIAL_ADMIN_SETUP_TOKEN` (opcional si usarás configuración inicial por web)
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSL_MODE` (y `DB_SSL_CA` si tu proveedor exige certificado CA)
4. Despliega (`Deploy`) y verifica en producción:
   - `https://<tu-proyecto>.vercel.app/` (Interfaz React)
   - `https://<tu-proyecto>.vercel.app/admin/` (Django Admin)
   - `https://<tu-proyecto>.vercel.app/api/docs/` (Swagger UI)
   - `https://<tu-proyecto>.vercel.app/api/health/` (`SELECT 1` contra MariaDB/MySQL en la nube)

---

## 4. Plantilla de tabla de pruebas de extremo a extremo (Informe Moodle)

| # | Operación en Django / Web / Swagger | Resultado esperado | Resultado obtenido | Verificación en MariaDB remota |
| --- | --- | --- | --- | --- |
| 1 | `GET /api/health/` | HTTP 200 con `database: ok`, `engine: mysql` | | `SELECT 1;` |
| 2 | Inicio de sesión como Administrador y Estudiante | JWT válido y acceso diferenciado por rol | | Tabla `auth_user` y `core_sesionjwt` |
| 3 | Crear y editar pregunta desde Django (`/admin/` o Gestión) | Pregunta guardada y actualizada sin errores | | `SELECT * FROM core_pregunta ORDER BY id DESC LIMIT 5;` |
| 4 | Eliminar registro de prueba no relacionado (ej. Categoría de prueba) | Registro eliminado de forma definitiva | | `SELECT * FROM core_categoria;` |
| 5 | Presentar simulacro como estudiante (temporizador, responder, enviar) | Cierre del intento y cálculo `Decimal` de calificación | | `SELECT id, usuario_id, puntaje, estado FROM core_intento ORDER BY id DESC LIMIT 5;` |
| 6 | Consultar `/api/reportes/` con filtros `anio`, `curso`, `eje` | Resultados filtrados consistentes con la BD | | Contraste con `core_intento` y `core_respuestaintento` |
| 7 | `GET` y `POST` en Swagger (`/api/docs/`) autenticado y prueba 401/403 | 200/201 autenticado; 401 sin token / 403 sin permiso | | Confirmar registro creado visible en BD y en Django |
