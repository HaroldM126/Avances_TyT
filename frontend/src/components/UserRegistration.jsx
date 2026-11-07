import { useEffect, useState } from 'react'
import * as api from '../api/recursos'

const EMPTY_FORM = {
  nombres: '',
  apellidos: '',
  numero_identidad: '',
  password: '',
  password_confirmation: '',
  curso: '',
}

export default function UserRegistration({ type, onDone }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [courses, setCourses] = useState([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const isStudent = type === 'student'

  useEffect(() => {
    if (!isStudent) return undefined
    api.obtenerCursosAcademicos().then(setCourses).catch((reason) => setError(reason.message))
    return undefined
  }, [isStudent])

  function set(key, value) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload = { ...form }
      if (!isStudent) delete payload.curso
      if (isStudent) await api.registrarEstudiante(payload)
      else await api.registrarDocente(payload)
      onDone()
    } catch (reason) {
      setError(reason.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="editor-form" onSubmit={submit} noValidate>
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isStudent ? 'Nuevo estudiante' : 'Nuevo docente'}</p>
          <h2>Registrar {isStudent ? 'estudiante' : 'docente'}</h2>
        </div>
      </div>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="registration-names">Nombres</label>
          <input id="registration-names" required value={form.nombres} onChange={(event) => set('nombres', event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="registration-last-names">Apellidos</label>
          <input id="registration-last-names" required value={form.apellidos} onChange={(event) => set('apellidos', event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="registration-identity">Número de identidad</label>
          <input id="registration-identity" required inputMode="numeric" pattern="[0-9]{6,12}" value={form.numero_identidad} onChange={(event) => set('numero_identidad', event.target.value)} />
          <small>Se usará como nombre de usuario para iniciar sesión.</small>
        </div>
        {isStudent && (
          <div className="field">
            <label htmlFor="registration-course">Curso / grupo</label>
            <select id="registration-course" required value={form.curso} onChange={(event) => set('curso', event.target.value)}>
              <option value="">Selecciona un curso</option>
              {courses.map((course) => <option key={course.id} value={course.id}>{course.nombre} · {course.periodo}</option>)}
            </select>
          </div>
        )}
        <div className="field">
          <label htmlFor="registration-password">Contraseña</label>
          <input id="registration-password" type="password" required minLength="8" value={form.password} onChange={(event) => set('password', event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="registration-password-confirmation">Confirmar contraseña</label>
          <input id="registration-password-confirmation" type="password" required minLength="8" value={form.password_confirmation} onChange={(event) => set('password_confirmation', event.target.value)} />
        </div>
      </div>
      <p className="form-message">El rol se asignará automáticamente: {isStudent ? 'Estudiante' : 'Docente'}.</p>
      {error && <p className="form-message form-message--error" role="alert">{error}</p>}
      <div className="dialog-actions">
        <button className="secondary-button" type="button" onClick={onDone} disabled={saving}>Cancelar</button>
        <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Registrar usuario'}</button>
      </div>
    </form>
  )
}
