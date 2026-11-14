# Guía de instalación y presentación

Esta guía prepara una demostración local del flujo docente y estudiante. Los
comandos están escritos para PowerShell en Windows y deben ejecutarse desde la
carpeta raíz del proyecto.

## Cuentas para iniciar sesión

El proyecto no trae una cuenta docente con contraseña fija. Crea el
administrador localmente y define sus credenciales al ejecutar
`createsuperuser`. Después registra el docente desde la plataforma; su usuario
será el número de identidad y su contraseña será la que se defina en el
formulario.

Al ejecutar `seed_reportes`, se crean seis estudiantes locales:

| Usuario | Contraseña |
| --- | --- |
| `demo_estudiante_1` a `demo_estudiante_6` | `TyT-Demo-2026!` |

Estas credenciales son solo para la base local de demostración. No se deben
usar en un servidor compartido o de producción.

## Requisitos

- Python 3.11 o posterior.
- Node.js LTS y npm.
- Para una presentación local se puede usar SQLite, que viene con Python. Para
  una instalación compartida, configura MySQL y sus variables de entorno.

## Instalación local

1. Clona la rama de entrega y entra a la carpeta:

   ```powershell
   git clone --branch feat/evaluation-presentation-guide https://github.com/HaroldM126/Avances_TyT.git
   cd Avances_TyT
   ```

2. Crea y activa un entorno virtual, e instala las dependencias de Python:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   Si PowerShell impide activar el entorno, ejecuta
   `Set-ExecutionPolicy -Scope Process Bypass` en esa terminal y repite la
   activación.

3. Usa SQLite para la demo, aplica migraciones, crea la cuenta administradora
   y carga los datos de ejemplo:

   ```powershell
   $env:DJANGO_USE_SQLITE = '1'
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py seed_reportes
   ```

   Guarda el usuario y contraseña que elegiste para el superusuario. El comando
   de demostración crea cursos, estudiantes y evaluaciones de ejemplo.

4. En una terminal, desde la raíz del proyecto, arranca Django:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   $env:DJANGO_USE_SQLITE = '1'
   python manage.py runserver
   ```

5. En otra terminal, instala y arranca la interfaz:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

6. Abre la dirección que indique Vite, normalmente `http://localhost:5173`.
   El backend Django escucha en `http://127.0.0.1:8000`.

Para MySQL, no definas `DJANGO_USE_SQLITE`; configura `MYSQL_DATABASE`,
`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST` y `MYSQL_PORT` antes de ejecutar
`migrate`. No hay credenciales MySQL incluidas en el proyecto.

## Preparar el rol docente

1. Inicia sesión con el superusuario creado en la instalación.
2. Ve a **Gestión → Usuarios → Registrar docente**. Define nombres, apellidos,
   número de identidad y una contraseña. El número de identidad será el usuario
   de acceso.
3. Ve a **Gestión → Roles → Docente** y habilita estos permisos:
   - Administrar banco de preguntas (`manage_question_bank`).
   - Configurar cuestionarios (`configure_quizzes`).
   - Consultar resultados (`view_results`).
   - Consultar reportes (`ver_reportes`).
4. Cierra la sesión del administrador e inicia como docente con el número de
   identidad y la contraseña definida.

El seed crea los cursos `Grupo TyT A` y `Grupo TyT B`; los estudiantes demo ya
están matriculados en esos grupos.

## Guion para presentar las funcionalidades

### 1. Preparación docente

1. En **Gestión → Categorías y competencias**, crea una categoría y uno o más
   ejes temáticos para las preguntas.
2. En **Gestión → Cuestionarios**, crea un cuestionario. Completa título,
   descripción, asignatura o temática, curso, apertura y cierre, duración,
   intentos permitidos y nota de aprobación. Déjalo en borrador.
3. En **Gestión → Importar preguntas**, descarga la plantilla Excel. La hoja
   **Instrucciones** explica el formato. Selecciona el cuestionario en borrador,
   diligencia la hoja **Preguntas** y carga el archivo.
4. Revisa el conteo y los errores por fila. Para demostrar la validación, deja
   una celda obligatoria vacía o escribe una respuesta correcta distinta de
   A–D; corrígela y vuelve a validar. Confirma cuando todas las filas estén
   válidas.
5. Regresa a **Cuestionarios**, edita el borrador y comprueba que las preguntas
   importadas quedaron asignadas. Elige si la calificación se publica al
   entregar y, si quieres mostrar el acceso protegido, define una contraseña.
6. Activa el cuestionario. La publicación exige fechas configuradas y
   preguntas activas con opciones válidas.

Usa una apertura igual o anterior a la hora actual y una hora de cierre
posterior. Asigna el cuestionario a `Grupo TyT A` para probarlo con los
primeros estudiantes demo.

### 2. Resolución como estudiante

1. Cierra la sesión docente e inicia con `demo_estudiante_1` y
   `TyT-Demo-2026!`.
2. Comprueba que aparece el cuestionario asignado al grupo. Inicia el intento,
   introduce la contraseña de acceso si la configuraste y responde las
   preguntas.
3. Finaliza y confirma la entrega. Si la publicación de la nota está apagada,
   el estudiante verá el mensaje de entrega registrada y no la calificación.
4. Para probar el límite de intentos, configura el cuestionario con un intento
   máximo y comprueba que no se puede abrir otro después de entregar.

### 3. Consulta docente

1. Cierra la sesión del estudiante e inicia otra vez como docente.
2. Abre **Gestión → Resultados** y selecciona el cuestionario.
3. Presenta participantes, intentos, aprobados, reprobados, promedio,
   distribución de calificaciones, aciertos por pregunta y porcentaje de
   aciertos por eje.
4. Si la nota estaba oculta, edita el cuestionario, activa la publicación del
   resultado y vuelve a la cuenta estudiante para comprobar que ya aparece.
5. Como comprobación de permisos, intenta abrir desde la cuenta estudiante la
   ruta de gestión. No debe mostrar los resultados privados del docente.

## Reiniciar la demo

La base SQLite se guarda en `db.sqlite3`. Para empezar de cero, detén Django y
elimina ese archivo local; luego repite `migrate`, `createsuperuser` y
`seed_reportes`. Esto borra las cuentas y los resultados locales de la demo.
