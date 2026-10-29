import { apiRequest } from './client'

export function obtenerCuestionariosDisponibles() {
  return apiRequest('/api/cuestionarios/disponibles/')
}

export function iniciarIntento(cuestionarioId) {
  return apiRequest(`/api/cuestionarios/${cuestionarioId}/iniciar/`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function cerrarSesion(refresh) {
  return apiRequest('/api/auth/logout/', {
    method: 'POST',
    body: JSON.stringify({ refresh }),
  })
}
