const ACCESS_TOKEN_KEY = 'simulador.access'
const REFRESH_TOKEN_KEY = 'simulador.refresh'

export async function iniciarSesion({ username, password }) {
  const response = await fetch('/api/auth/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(
      payload.detail || 'No pudimos iniciar sesión. Revisa tus datos.',
    )
  }

  const payload = await response.json()
  guardarTokens(payload)
  return payload
}

export async function cambiarContrasena(data) {
  const response = await fetch('/api/auth/change-password/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${obtenerToken()}`,
    },
    body: JSON.stringify(data),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const firstError = Object.values(payload)[0]
    throw new Error(Array.isArray(firstError) ? firstError[0] : firstError || 'No pudimos actualizar la contraseña.')
  }
  return payload
}

export async function configurarAdministradorInicial(data) {
  const { setup_token, ...account } = data
  const response = await fetch('/api/auth/initial-admin/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Initial-Admin-Token': setup_token,
    },
    body: JSON.stringify(account),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const firstError = Object.values(payload)[0]
    throw new Error(
      Array.isArray(firstError)
        ? firstError[0]
        : firstError || 'No pudimos configurar el administrador inicial.',
    )
  }
  return payload
}

export function cerrarSesionLocal() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function obtenerToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function obtenerRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function guardarTokens(payload) {
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.access)
  if (payload.refresh) {
    localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh)
  }
}
