import { useEffect, useMemo, useState } from 'react'
import {
  exportarReporte,
  obtenerConsultaReporte,
  obtenerHistorialReporte,
  obtenerOpcionesReportes,
} from '../api/recursos'

const REPORTS = [
  ['consolidado', 'Consolidado general'],
  ['periodos', 'Resultados por año y período'],
  ['cursos', 'Resultados por curso'],
  ['ejes', 'Desempeño por eje temático'],
  ['calificaciones', 'Calificaciones por estudiante'],
  ['historial', 'Historial individual'],
  ['dificultad', 'Preguntas de mayor dificultad'],
]

const EMPTY_FILTERS = {
  anio: '',
  periodo: '',
  curso: '',
  eje: '',
  estudiante: '',
  buscar: '',
  ordenar: 'fecha',
  direccion: 'desc',
}

const ATTEMPT_STATUS_LABELS = {
  EN_CURSO: 'En curso',
  ENVIADO: 'Enviado',
  VENCIDO: 'Vencido',
  ANULADO: 'Anulado',
}

const GRADE_FIELDS = new Set([
  'calificacion',
  'puntaje',
  'promedio',
  'minima',
  'maxima',
  'nota_promedio',
])

const COLUMNS = {
  consolidado: [
    ['estudiante', 'Estudiante'],
    ['curso', 'Curso'],
    ['periodo', 'Período'],
    ['simulacro', 'Simulacro'],
    ['fecha', 'Fecha'],
    ['calificacion', 'Calificación'],
    ['estado', 'Estado'],
  ],
  calificaciones: [
    ['estudiante', 'Estudiante'],
    ['curso', 'Curso'],
    ['simulacro', 'Simulacro'],
    ['fecha', 'Fecha'],
    ['calificacion', 'Nota sobre 5'],
    ['estado', 'Estado'],
  ],
  periodos: [
    ['periodo__anio', 'Año'],
    ['periodo__nombre', 'Período'],
    ['evaluaciones', 'Evaluaciones finalizadas'],
    ['promedio', 'Promedio'],
  ],
  cursos: [
    ['curso__nombre', 'Curso'],
    ['periodo__nombre', 'Período'],
    ['estudiantes_distintos', 'Estudiantes evaluados'],
    ['promedio', 'Promedio'],
    ['minima', 'Mínima'],
    ['maxima', 'Máxima'],
  ],
  ejes: [
    ['intento__periodo__anio', 'Año'],
    ['intento__periodo__nombre', 'Período'],
    ['intento__curso__nombre', 'Curso'],
    ['pregunta__competencia__nombre', 'Eje temático'],
    ['respuestas_registradas', 'Respuestas registradas'],
    ['aciertos', 'Aciertos'],
    ['errores', 'Errores'],
    ['porcentaje_aciertos', '% de aciertos'],
    ['nota_promedio', 'Nota promedio'],
  ],
  historial: [
    ['fecha', 'Fecha del intento'],
    ['curso__nombre', 'Curso'],
    ['periodo__nombre', 'Período'],
    ['cuestionario__nombre', 'Simulacro'],
    ['preguntas_respondidas', 'Respondidas'],
    ['aciertos', 'Aciertos'],
    ['puntaje', 'Nota final'],
    ['estado', 'Estado'],
  ],
  dificultad: [
    ['pregunta_id', 'ID pregunta'],
    ['pregunta__enunciado', 'Pregunta'],
    ['pregunta__competencia__nombre', 'Eje temático'],
    ['respuestas_registradas', 'Respuestas'],
    ['errores', 'Errores'],
    ['porcentaje_aciertos', '% de aciertos'],
  ],
}

function display(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (ATTEMPT_STATUS_LABELS[value]) return ATTEMPT_STATUS_LABELS[value]
  if (typeof value === 'string' && value.includes('T')) {
    const date = new Date(value)
    if (!Number.isNaN(date.getTime())) return date.toLocaleString('es-CO')
  }
  return value
}

function formatGrade(value) {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : display(value)
}

function buildParams(values, extra = {}) {
  return Object.fromEntries(
    Object.entries({ ...values, ...extra }).filter(
      ([, value]) => value !== '' && value !== null && value !== undefined,
    ),
  )
}

export default function Reportes({ canSeeIdentification, isStudent }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [options, setOptions] = useState({
    anios: [],
    periodos: [],
    cursos: [],
    ejes: [],
    estudiantes: [],
  })
  const [type, setType] = useState('consolidado')
  const [applied, setApplied] = useState(null)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    obtenerOpcionesReportes(buildParams(filters))
      .then((result) => {
        if (active) setOptions(result)
      })
      .catch((reason) => {
        if (active) setError(reason.message)
      })
    return () => { active = false }
  }, [
    filters.anio,
    filters.periodo,
    filters.curso,
    filters.eje,
    filters.estudiante,
    filters.buscar,
  ])

  useEffect(() => {
    if (!applied) return undefined
    let active = true
    setLoading(true)
    setError('')
    obtenerConsultaReporte(buildParams(applied, { tipo: type, pagina: page }))
      .then((result) => {
        if (active) setData(result)
      })
      .catch((reason) => {
        if (active) setError(reason.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [applied, type, page])

  const columns = useMemo(() => {
    const base = COLUMNS[type] || COLUMNS.consolidado
    if (canSeeIdentification && ['consolidado', 'calificaciones'].includes(type)) {
      return [...base.slice(0, 1), ['identificacion', 'Identificación'], ...base.slice(1)]
    }
    return base
  }, [canSeeIdentification, type])

  function changeFilter(key, value) {
    const descendants = {
      anio: ['periodo', 'curso', 'eje', 'estudiante'],
      periodo: ['curso', 'eje', 'estudiante'],
      curso: ['eje', 'estudiante'],
      eje: ['estudiante'],
    }
    setFilters((current) => {
      const next = { ...current, [key]: value }
      for (const child of descendants[key] || []) next[child] = ''
      return next
    })
  }

  function consult(event) {
    event.preventDefault()
    setPage(1)
    setApplied({ ...filters })
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS)
    setPage(1)
    setApplied({ ...EMPTY_FILTERS })
  }

  async function download() {
    const exportType = type === 'ejes' ? 'ejes' : type === 'historial' ? 'historial' : 'consolidado'
    setDownloading(true)
    setError('')
    try {
      const file = await exportarReporte(exportType, buildParams(applied || filters))
      const url = URL.createObjectURL(file.blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = file.filename
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (reason) {
      setError(reason.message)
    } finally {
      setDownloading(false)
    }
  }

  async function openHistory(studentId, studentName) {
    setError('')
    try {
      const rows = await obtenerHistorialReporte(
        studentId,
        buildParams(applied || filters),
      )
      setHistory({ studentName, rows })
    } catch (reason) {
      setError(reason.message)
    }
  }

  const indicatorCards = [
    ['Estudiantes distintos', data?.indicadores?.estudiantes_distintos],
    ['Intentos finalizados', data?.indicadores?.intentos_finalizados],
    ['Promedio', formatGrade(data?.indicadores?.promedio)],
    ['Nota mínima', formatGrade(data?.indicadores?.minima)],
    ['Nota máxima', formatGrade(data?.indicadores?.maxima)],
    ['Aprobación', data?.indicadores?.porcentaje_aprobacion == null
      ? null
      : `${data.indicadores.porcentaje_aprobacion}%`],
  ]

  return (
    <section className="management-section reportes">
      <header className="section-heading">
        <div>
          <p className="eyebrow">Seguimiento académico</p>
          <h2>Consultas y reportes</h2>
        </div>
      </header>
      <p className="section-intro">
        Las métricas se calculan con intentos finalizados que tienen nota.
        Los intentos sin finalizar se conservan en el historial y no alteran
        promedios, mínimas, máximas ni aprobación.
      </p>
      <form className="report-filters" onSubmit={consult}>
        <label className="field">
          <span>Año</span>
          <select value={filters.anio} onChange={(event) => changeFilter('anio', event.target.value)}>
            <option value="">Todos</option>
            {options.anios.map((year) => <option key={year} value={year}>{year}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Período</span>
          <select value={filters.periodo} onChange={(event) => changeFilter('periodo', event.target.value)}>
            <option value="">Todos</option>
            {options.periodos.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Curso / grupo</span>
          <select value={filters.curso} onChange={(event) => changeFilter('curso', event.target.value)}>
            <option value="">Todos</option>
            {options.cursos.map((item) => <option key={item.id} value={item.id}>{item.nombre} · {item.periodo}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Eje temático</span>
          <select value={filters.eje} onChange={(event) => changeFilter('eje', event.target.value)}>
            <option value="">Todos</option>
            {options.ejes.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Estudiante</span>
          <select value={filters.estudiante} onChange={(event) => changeFilter('estudiante', event.target.value)}>
            <option value="">Todos</option>
            {options.estudiantes.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Búsqueda por nombre, usuario o identificación</span>
          <input
            value={filters.buscar}
            maxLength="100"
            onChange={(event) => changeFilter('buscar', event.target.value)}
            placeholder="Nombre o usuario"
          />
        </label>
        <label className="field">
          <span>Ordenar por</span>
          <select value={filters.ordenar} onChange={(event) => setFilters((current) => ({ ...current, ordenar: event.target.value }))}>
            <option value="fecha">Fecha</option>
            <option value="nombre">Nombre</option>
            <option value="calificacion">Calificación</option>
          </select>
        </label>
        <label className="field">
          <span>Dirección</span>
          <select value={filters.direccion} onChange={(event) => setFilters((current) => ({ ...current, direccion: event.target.value }))}>
            <option value="desc">Mayor a menor / más reciente</option>
            <option value="asc">Menor a mayor / más antiguo</option>
          </select>
        </label>
        <label className="field">
          <span>Consulta</span>
          <select value={type} onChange={(event) => setType(event.target.value)}>
            {REPORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <div className="report-actions">
          <button className="primary-button" type="submit">Consultar</button>
          <button className="secondary-button" type="button" onClick={clearFilters}>Limpiar filtros</button>
          <button
            className="secondary-button"
            type="button"
            onClick={download}
            disabled={downloading || (type === 'historial' && !filters.estudiante && !isStudent)}
          >
            {downloading ? 'Preparando Excel…' : 'Exportar a Excel'}
          </button>
        </div>
      </form>

      <p className="report-threshold">
        <strong>Umbral de aprobación:</strong> se usa la nota mínima configurada
        en cada cuestionario{data?.indicadores?.umbrales_aprobacion?.length
          ? ` (${data.indicadores.umbrales_aprobacion.join(', ')})`
          : ''}.
      </p>
      {data && (
        <div className="report-indicators">
          {indicatorCards.map(([label, value]) => (
            <article className="report-indicator" key={label}>
              <span>{label}</span>
              <strong>{display(value)}</strong>
            </article>
          ))}
          <article className="report-indicator report-indicator--wide">
            <span>Intentos aprobados / no aprobados</span>
            <strong>{data.indicadores.aprobados} / {data.indicadores.no_aprobados}</strong>
          </article>
        </div>
      )}
      {error && <p className="form-message form-message--error" role="alert">{error}</p>}
      {loading && <div className="state-block" role="status"><span className="loading-dot" aria-hidden="true" /><p>Consultando resultados…</p></div>}
      {!loading && !data && !error && <div className="empty-state"><p>Selecciona los filtros y pulsa «Consultar» para ver los resultados.</p></div>}
      {!loading && data && data.results.length === 0 && (
        <div className="empty-state"><h2>Sin resultados</h2><p>No hay registros para los filtros seleccionados.</p></div>
      )}
      {!loading && data && data.results.length > 0 && (
        <>
          <div className="report-table-wrap">
            <table className="report-table">
              <thead><tr>
                {columns.map(([, label]) => <th key={label}>{label}</th>)}
                {['consolidado', 'calificaciones'].includes(type) && <th>Historial</th>}
              </tr></thead>
              <tbody>
                {data.results.map((row, index) => {
                  const studentId = row.estudiante_id || row.usuario_id
                  const studentName = row.estudiante || `${row['usuario__first_name'] || ''} ${row['usuario__last_name'] || ''}`.trim() || row['usuario__username']
                  return (
                    <tr key={row.id || `${type}-${index}`}>
                      {columns.map(([key]) => {
                        const value = key === 'estudiante' ? studentName : row[key]
                        return (
                          <td key={key}>
                            {GRADE_FIELDS.has(key) ? formatGrade(value) : display(value)}
                          </td>
                        )
                      })}
                      {['consolidado', 'calificaciones'].includes(type) && (
                        <td>
                          {studentId
                            ? <button className="text-button" type="button" onClick={() => openHistory(studentId, studentName)}>Ver historial</button>
                            : '—'}
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="report-pagination">
            <span>{data.count} registros · página {page} de {Math.max(1, Math.ceil(data.count / 10))}</span>
            <div>
              <button className="secondary-button" type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={!data.previous}>Anterior</button>
              <button className="secondary-button" type="button" onClick={() => setPage((value) => value + 1)} disabled={!data.next}>Siguiente</button>
            </div>
          </div>
        </>
      )}

      {history && (
        <div className="dialog-backdrop report-history-backdrop">
          <section className="confirm-dialog report-history" role="dialog" aria-modal="true" aria-labelledby="history-title">
            <div className="section-heading">
              <div><p className="eyebrow">Evolución de calificaciones</p><h2 id="history-title">{history.studentName}</h2></div>
              <button className="text-button" type="button" onClick={() => setHistory(null)}>Cerrar</button>
            </div>
            {!history.rows.length
              ? <p>Este estudiante aún no tiene intentos.</p>
              : <div className="report-table-wrap"><table className="report-table">
                <thead><tr><th>Fecha</th><th>Período</th><th>Simulacro</th><th>Respondidas</th><th>Aciertos</th><th>Nota</th><th>Estado</th></tr></thead>
                <tbody>{history.rows.map((row) => <tr key={row.id}>
                  <td>{display(row.fecha)}</td>
                  <td>{display(row['periodo__nombre'])}</td>
                  <td>{row['cuestionario__nombre']}</td>
                  <td>{row.preguntas_respondidas}</td>
                  <td>{row.aciertos}</td>
                  <td>{formatGrade(row.puntaje)}</td>
                  <td>{row.estado}</td>
                </tr>)}</tbody>
              </table></div>}
            <button className="secondary-button" type="button" onClick={() => setHistory(null)}>Cerrar historial</button>
          </section>
        </div>
      )}
    </section>
  )
}
