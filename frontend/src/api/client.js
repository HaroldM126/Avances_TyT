import {
  cerrarSesionLocal,
  guardarTokens,
  obtenerRefreshToken,
  obtenerToken,
} from './auth'

let renovacionEnCurso = null

async function renovarToken() {
  if (!renovacionEnCurso) {
    renovacionEnCurso = fetch('/api/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: obtenerRefreshToken() }),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('La sesión terminó.')
        const payload = await response.json()
        guardarTokens(payload)
        return payload.access
      })
      .finally(() => {
        renovacionEnCurso = null
      })
  }
  return renovacionEnCurso
}

function mensajeError(payload) {
  if (payload?.detail) return payload.detail
  if (payload && typeof payload === 'object') {
    const first = Object.values(payload).flat(Infinity).find(Boolean)
    if (first) return String(first)
  }
  return 'No pudimos completar la solicitud. Inténtalo de nuevo.'
}

export async function apiRequest(path, options = {}, puedeRenovar = true) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  const token = obtenerToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(path, { ...options, headers })

  if (response.status === 401 && puedeRenovar && obtenerRefreshToken()) {
    try {
      await renovarToken()
      return apiRequest(path, options, false)
    } catch {
      cerrarSesionLocal()
      throw new Error('Tu sesión terminó. Inicia sesión nuevamente.')
    }
  }
  if (response.status === 401) {
    cerrarSesionLocal()
    throw new Error('Tu sesión terminó. Inicia sesión nuevamente.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(mensajeError(payload))
    error.payload = payload
    throw error
  }
  if (response.status === 204 || response.status === 205) return null
  return response.json()
}

export async function descargarArchivo(path) {
  const response = await fetch(path, {
    headers: { Authorization: `Bearer ${obtenerToken()}` },
  })
  if (!response.ok) throw new Error('No pudimos descargar el archivo.')
  return response.blob()
}
