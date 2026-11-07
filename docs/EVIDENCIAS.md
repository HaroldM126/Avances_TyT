# Evidencias del módulo de consultas y reportes

## Modelo y ruta de calificación

El diagrama y las relaciones se documentan en
[ESQUEMA_MODELOS.md](./ESQUEMA_MODELOS.md). La ruta principal es:

`Estudiante -> Intento -> RespuestaIntento -> Pregunta -> Competencia (eje) /
Categoría -> calificación del Intento`.

El curso y el período se guardan en FKs nullable de `Intento`. Al crear un
intento, se copian el curso y el período del cuestionario. Los intentos previos
a esta funcionalidad quedan sin esas relaciones; no se actualizan
calificaciones ni respuestas históricas.

La calificación real existente se calcula así:

`(puntaje de respuestas correctas / puntaje total de preguntas) * nota_maxima`

El modelo usa `Decimal`, redondeo `ROUND_HALF_UP` a dos decimales y compara la
nota con `Cuestionario.nota_aprobar`. El frontend y los archivos incluyen la
nota mínima configurada en los cuestionarios filtrados, que puede variar entre
evaluaciones. No se asigna una nota por eje: no hay una fórmula de nota por eje
definida en el dominio.

## Decisiones de consulta

- Los intentos no finalizados o sin `fecha_envio` se excluyen del promedio,
  mínima, máxima y porcentaje de aprobación. Se cuentan como intentos
  finalizados solo si fueron enviados y tienen una calificación.
- El porcentaje de aprobación se calcula respecto a los intentos finalizados
  con nota; las tarjetas separan esa cantidad de estudiantes distintos.
- Las tablas y el historial también muestran intentos en curso; su calificación
  aparece vacía. Esto permite conservar seguimiento sin contaminar las métricas.
- Las estadísticas por eje y por dificultad cuentan exclusivamente respuestas
  con opción seleccionada. No infieren respuestas para filas vacías.
- Una competencia no tiene una regla propia de calificación; `nota_promedio`
  por eje siempre es `null`.
- Las identificaciones viven en `Matricula` y solo aparecen con
  `ver_identificacion_estudiante`. El permiso de consulta general no revela por
  sí solo esa información.
- `ver_reportes` habilita los reportes globales a administradores y docentes
  autorizados. El rol `Estudiante` obtiene solo su propio alcance. Un intento
  ajeno se responde como no encontrado.

## Endpoints

| Endpoint | Uso |
|---|---|
| `GET /api/reportes/filtros/` | Opciones jerárquicas de año, período, curso, eje y estudiante |
| `GET /api/reportes/` | Consulta principal paginada |
| `GET /api/reportes/consultas/` | Alias explícito para consulta paginada |
| `GET /api/reportes/historial/{estudiante_id}/` | Historial de un estudiante |
| `GET /api/reportes/exportar/consolidado/` | Excel A, detalle y promedio por estudiante |
| `GET /api/reportes/exportar/ejes/` | Excel B, respuestas y aciertos por eje |
| `GET /api/reportes/exportar/historial/` | Excel C, intentos cronológicos de un estudiante |
| `GET /api/cursos-academicos/` | Cursos para asignación a cuestionarios |

Parámetros de consulta: `anio`, `periodo`, `curso`, `eje`, `estudiante`,
`buscar`, `tipo`, `ordenar`, `direccion` y `pagina`. Los filtros hijos se
validan contra sus padres; los identificadores inválidos se rechazan.

## Consultas ORM y exportación

`core/services/reportes.py` centraliza `aplicar_filtros(queryset, params,
user)`. Las vistas de filtros, consulta, historial y exportación invocan este
helper para mantener el mismo alcance y aislamiento. Las agregaciones emplean
`Count`, `Avg`, `Min`, `Max`, `Q` y `F` en el ORM; las consultas paginadas se
limitan a 10 filas en base de datos. Para presentar filas de intentos se usan
`select_related` y una subconsulta de matrícula para la identificación.

El cálculo de aprobación en la consulta no fija un `3.0` general. Compara cada
intento con el umbral de su cuestionario en la base de datos:

```python
aprobados=Count(
    'id',
    filter=Q(puntaje__gte=F('cuestionario__nota_aprobar')),
)
```

El helper de finalización excluye filas abiertas de las métricas:

```python
return queryset.filter(
    enviado=True,
    fecha_envio__isnull=False,
    puntaje__isnull=False,
)
```

`core/views_reportes.py` construye libros `.xlsx` con `openpyxl`, metadatos de
generación y filtros, umbral(es), encabezados, formato numérico, ajuste de ancho,
filas congeladas y autofiltro. La exportación evalúa el queryset completo y no
la página actual; cuando no hay datos, conserva encabezados y agrega `Sin
resultados`.

## Datos de demostración

El comando `seed_reportes` crea de forma idempotente:

- Dos años y cuatro períodos (2025-1, 2025-2, 2026-1 y 2026-2).
- Dos cursos en períodos de 2026.
- Seis estudiantes, con matrículas e identificaciones ficticias.
- Dos cuestionarios que cubren Lectura crítica, Comprensión ciudadana y
  Pensamiento crítico.
- Seis intentos base y 18 intentos finalizados adicionales para paginación,
  repartidos entre `2026-1` y `2026-2` y los seis estudiantes demo; también
  crea dos intentos en curso.
- Las notas de los intentos adicionales varían entre 1.50 y 5.00; incluyen
  aprobados y no aprobados, y registran respuestas en los tres ejes temáticos.
- Los intentos y respuestas existentes no se reescriben al repetir el comando.

Los usuarios de ejemplo son `demo_estudiante_1` a `demo_estudiante_6`, con
contraseña `TyT-Demo-2026!`. Son datos locales de demostración.

## Guía de demo en vivo

1. Configura la conexión a MySQL o usa SQLite para la demo:

   ```powershell
   $env:DJANGO_USE_SQLITE = '1'
   python manage.py migrate
   python manage.py seed_reportes
   python manage.py createsuperuser
   python manage.py runserver
   ```

2. En otra terminal, inicia el frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

3. Inicia sesión con el superusuario. En «Gestión», muestra «Consultas y
   reportes» y las tarjetas de estudiantes distintos, intentos, promedios,
   extremos y aprobación. Explica que la nota de aprobación viene del
   cuestionario.
4. Filtra por año `2026`, período `2026-1` y grupo `Grupo TyT A`; comprueba que
   las opciones hijas se ajustan a la selección.
5. Cambia la consulta a desempeño por eje para mostrar respuestas contestadas,
   aciertos y errores. La columna de nota promedio por eje queda vacía porque no
   existe una regla de cálculo en los modelos.
6. Selecciona un estudiante y el historial individual para revisar la secuencia
   cronológica; las filas en curso no tienen calificación final.
7. Descarga el consolidado o el reporte por eje y abre el libro para mostrar
   metadatos, filtros, umbral de aprobación, autofiltro y filas de resultados.

## Validación ejecutada

- `python manage.py check`: sin problemas.
- `DJANGO_USE_SQLITE=1 python manage.py test core`: 24 pruebas aprobadas.
- `python manage.py makemigrations --check --dry-run`: no detecta cambios de
  modelos pendientes. Django mostró una advertencia al intentar consultar el
  MySQL local, que no acepta la conexión predeterminada; la migración se aplicó
  de todas formas en una base SQLite temporal aislada.
- `npm run build` desde `frontend/`: compilación de producción aprobada.
- `seed_reportes` se ejecutó dos veces en la SQLite local: conservó los 28
  intentos y 80 respuestas que ya existían, y dejó exactamente los mismos 18
  intentos de paginación en ambas ejecuciones. Sus notas fueron 1.50, 1.67,
  3.17, 3.33, 3.50 y 5.00; están repartidos entre los dos períodos y seis
  estudiantes. En una base nueva, junto con los datos base, el seed crea 24
  intentos finalizados y 2 en curso.
