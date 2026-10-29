import { apiRequest, descargarArchivo } from './client'
import { obtenerToken } from './auth'

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
export const obtenerRoles = () => apiRequest('/api/roles/')
export const guardarRol = (data, id) =>
  apiRequest(id ? `/api/roles/${id}/` : '/api/roles/', {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(data),
  })
export const eliminarRol = (id) =>
  apiRequest(`/api/roles/${id}/`, { method: 'DELETE' })
export const obtenerPermisos = () => apiRequest('/api/permissions/')
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
