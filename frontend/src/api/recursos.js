import { apiRequest, descargarArchivo } from './client'
import {
  cerrarSesionLocal,
  guardarTokens,
  obtenerRefreshToken,
  obtenerToken,
} from './auth'

export const obtenerMe = () => apiRequest('/api/auth/me/')
export const obtenerIntento = (id) => apiRequest(`/api/intentos/${id}/`)
export const guardarRespuesta = (id, data) =>
  apiRequest(`/api/intentos/${id}/respuestas/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
export const enviarIntento = (id) =>
  apiRequest(`/api/intentos/${id}/enviar/`, { method: 'POST', body: '{}' })
export const obtenerRevision = (id) => apiRequest(`/api/intentos/${id}/revision/`)
export const obtenerIntentos = () => apiRequest('/api/intentos/')
export const marcarRespuesta = (id, pregunta, marcada_revision) =>
  guardarRespuesta(id, { pregunta, marcada_revision })

export const obtenerPreguntas = (params = '') => apiRequest(`/api/preguntas/${params}`)
export const obtenerPregunta = (id) => apiRequest(`/api/preguntas/${id}/`)
export const guardarPregunta = (data, id) =>
  apiRequest(id ? `/api/preguntas/${id}/` : '/api/preguntas/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })
export const cambiarEstadoPregunta = (id, activa) =>
  apiRequest(`/api/preguntas/${id}/${activa ? 'activar' : 'desactivar'}/`, {
    method: 'POST',
    body: '{}',
  })
export const obtenerCategorias = () => apiRequest('/api/categorias/')
export const obtenerCompetencias = () => apiRequest('/api/competencias/')
export const guardarCategoria = (data, id) =>
  apiRequest(id ? `/api/categorias/${id}/` : '/api/categorias/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })
export const guardarCompetencia = (data, id) =>
  apiRequest(id ? `/api/competencias/${id}/` : '/api/competencias/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })

export const obtenerCuestionarios = () => apiRequest('/api/cuestionarios/')
export const obtenerCuestionario = (id) => apiRequest(`/api/cuestionarios/${id}/`)
export const guardarCuestionario = (data, id) =>
  apiRequest(id ? `/api/cuestionarios/${id}/` : '/api/cuestionarios/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })
export const cambiarEstadoCuestionario = (id, activo) =>
  apiRequest(`/api/cuestionarios/${id}/${activo ? 'activar' : 'desactivar'}/`, {
    method: 'POST',
    body: '{}',
  })

export const obtenerUsuarios = () => apiRequest('/api/users/')
export const guardarUsuario = (data, id) =>
  apiRequest(id ? `/api/users/${id}/` : '/api/users/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })
export const registrarEstudiante = (data) =>
  apiRequest('/api/users/estudiantes/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
export const registrarDocente = (data) =>
  apiRequest('/api/users/docentes/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
export const obtenerRoles = () => apiRequest('/api/roles/')
export const guardarRol = (data, id) =>
  apiRequest(id ? `/api/roles/${id}/` : '/api/roles/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })
export const eliminarRol = (id) =>
  apiRequest(`/api/roles/${id}/`, { method: 'DELETE' })
export const obtenerPermisos = () => apiRequest('/api/permissions/')
export const obtenerCursosAcademicos = () => apiRequest('/api/cursos-academicos/')
const queryParams = (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) search.set(key, value)
  })
  return search.toString()
}
export const obtenerOpcionesReportes = (params = {}) =>
  apiRequest(`/api/reportes/filtros/${queryParams(params) ? `?${queryParams(params)}` : ''}`)
export const obtenerConsultaReporte = (params = {}) =>
  apiRequest(`/api/reportes/consultas/?${queryParams(params)}`)
export const obtenerHistorialReporte = (id, params = {}) =>
  apiRequest(`/api/reportes/historial/${id}/?${queryParams(params)}`)
export async function exportarReporte(tipo, params = {}) {
  const url = `/api/reportes/exportar/${tipo}/?${queryParams(params)}`
  const request = (token) => fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  })
  let response = await request(obtenerToken())
  if (response.status === 401 && obtenerRefreshToken()) {
    const refreshed = await fetch('/api/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: obtenerRefreshToken() }),
    })
    if (!refreshed.ok) {
      cerrarSesionLocal()
      throw new Error('Tu sesión terminó. Inicia sesión nuevamente.')
    }
    const tokens = await refreshed.json()
    guardarTokens(tokens)
    response = await request(tokens.access)
  }
  if (response.status === 401) {
    cerrarSesionLocal()
    throw new Error('Tu sesión terminó. Inicia sesión nuevamente.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || 'No pudimos descargar el archivo.')
  }
  const disposition = response.headers.get('Content-Disposition') || ''
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1]
  return {
    blob: await response.blob(),
    filename: filename || `reporte_${tipo}.xlsx`,
  }
}
export const obtenerImportaciones = () => apiRequest('/api/preguntas/importar/')
export const obtenerImportacion = (id) =>
  apiRequest(`/api/preguntas/importar/${id}/`)
export const actualizarImportacion = (id, filas) =>
  apiRequest(`/api/preguntas/importar/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ filas }),
  })

export async function previsualizarImportacion(file) {
  const form = new FormData()
  form.append('archivo', file)
  const response = await fetch('/api/preguntas/importar/preview/', {
    method: 'POST',
    headers: { Authorization: `Bearer ${localStorage.getItem('simulador.access')}` },
    body: form,
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(payload.detail || 'No pudimos leer el archivo.')
    error.payload = payload
    throw error
  }
  return payload
}

export async function confirmarImportacion(id) {
  const form = new FormData()
  form.append('importacion_id', id)
  const response = await fetch('/api/preguntas/importar/confirmar/', {
    method: 'POST',
    headers: { Authorization: `Bearer ${obtenerToken()}` },
    body: form,
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || 'No pudimos confirmar la importación.')
  }
  return payload
}
export const descargarPlantilla = () =>
  descargarArchivo('/api/preguntas/importar/plantilla/')
