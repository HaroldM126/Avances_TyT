import { apiRequest } from './client'

export function obtenerCuestionariosDisponibles() {
  return apiRequest('/api/cuestionarios/disponibles/')
}

export function iniciarIntento(cuestionarioId, contrasena = '') {
  return apiRequest(`/api/cuestionarios/${cuestionarioId}/iniciar/`, {
    method: 'POST',
    body: JSON.stringify({ contrasena }),
  })
}

export function cerrarSesion(refresh) {
  return apiRequest('/api/auth/logout/', {
    method: 'POST',
    body: JSON.stringify({ refresh }),
  })
}
