import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  cerrarSesionLocal,
  cambiarContrasena,
  configurarAdministradorInicial,
  iniciarSesion,
  obtenerRefreshToken,
  obtenerToken,
} from './api/auth'
import {
  cerrarSesion,
  iniciarIntento,
  obtenerCuestionariosDisponibles,
} from './api/cuestionarios'
import * as api from './api/recursos'
import Reportes from './components/Reportes'
import UserRegistration from './components/UserRegistration'

const dateFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'long',
  timeStyle: 'short',
})
const shortDate = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' })

function App() {
  const location = useLocation()
  const token = obtenerToken()
  if (!token) return <Login />
  if (location.pathname.startsWith('/intentos/')) return <AttemptPage />
  if (location.pathname.startsWith('/resultados/')) return <ResultPage />
  if (location.pathname.startsWith('/gestion')) return <ManagementPage />
  return <Home />
}

function Brand() {
  return <div className="brand-mark brand-mark--dark" aria-label="Simulador TyT"><span className="brand-mark__line" /><span>TyT</span></div>
}

function Icon({ name }) {
  const paths = {
    user: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.7-3.1 3.2-5 7-5s6.3 1.9 7 5" /></>,
    logout: <><path d="M10 5H5v14h5" /><path d="m14 8 4 4-4 4" /><path d="M18 12H9" /></>,
    settings: <><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /><circle cx="12" cy="12" r="3.5" /></>,
    edit: <><path d="m4 16.5-.8 4.3 4.3-.8L19 8.5 15.5 5 4 16.5Z" /><path d="m13.5 7 3.5 3.5" /></>,
    download: <><path d="M12 3v12M7 10l5 5 5-5M4 20h16" /></>,
    questions: <><path d="M4 5h16v14H4zM8 9h8M8 13h5" /></>,
    catalog: <><path d="M5 5h14v14H5zM8 9h8M8 13h5" /></>,
    upload: <><path d="M12 16V4M7 9l5-5 5 5M4 20h16" /></>,
    quiz: <><path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" /></>,
    results: <><path d="M5 19V9M12 19V5M19 19v-7" /></>,
    reports: <><path d="M5 20V10M12 20V4M19 20v-7" /></>,
    roles: <><circle cx="9" cy="8" r="3" /><path d="M3 20c.4-3 2.4-5 6-5s5.6 2 6 5M16 5.5a3 3 0 0 1 0 5.8M16 15c2.8.2 4.3 1.8 4.7 4" /></>,
  }
  return <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[name] || paths.settings}</svg>
}

function Topbar({ title, onLogout, children }) {
  const [user, setUser] = useState(null)
  const [profileOpen, setProfileOpen] = useState(false)
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', new_password_confirmation: '' })
  const [profileError, setProfileError] = useState('')
  const [profileMessage, setProfileMessage] = useState('')
  useEffect(() => { api.obtenerMe().then(setUser).catch(() => {}) }, [])
  async function changePassword(event) {
    event.preventDefault()
    setProfileError('')
    setProfileMessage('')
    try {
      await cambiarContrasena(passwords)
      setPasswords({ current_password: '', new_password: '', new_password_confirmation: '' })
      setProfileMessage('Contraseña actualizada correctamente.')
    } catch (error) {
      setProfileError(error.message)
    }
  }
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || ''
  return <header className="topbar"><Brand /><span className="topbar-title">{title || ''}</span><div className="topbar-actions">{children}{fullName && <span className="topbar-user">{fullName}</span>}<button className="text-button" type="button" onClick={() => { setProfileOpen(!profileOpen); setProfileError(''); setProfileMessage('') }} aria-label="Abrir perfil"><Icon name="user" /><span className="sr-only">Perfil</span></button></div>{profileOpen && <div className="profile-popover"><div className="profile-popover__heading"><Icon name="user" /><div><strong>{fullName}</strong><span>{user?.roles?.join(', ') || 'Usuario'}</span></div></div><dl className="profile-details"><div><dt>Nombres</dt><dd>{user?.first_name || 'No registrado'}</dd></div><div><dt>Apellidos</dt><dd>{user?.last_name || 'No registrados'}</dd></div><div><dt>Cédula</dt><dd>{user?.numero_identidad || 'No registrada'}</dd></div>  <div><dt>Correo</dt><dd>{user?.email || 'No registrado'}</dd></div><div><dt>Curso / grupo</dt><dd>{user?.cursos?.join(', ') || 'No asignado'}</dd></div></dl><form onSubmit={changePassword}><h3>Cambiar contraseña</h3><div className="field"><label htmlFor="current-password">Contraseña actual</label><input id="current-password" type="password" required value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} /></div><div className="field"><label htmlFor="new-password">Nueva contraseña</label><input id="new-password" type="password" required minLength="8" value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} /></div><div className="field"><label htmlFor="new-password-confirmation">Confirmar contraseña</label><input id="new-password-confirmation" type="password" required minLength="8" value={passwords.new_password_confirmation} onChange={(event) => setPasswords({ ...passwords, new_password_confirmation: event.target.value })} /></div>{profileError && <p className="form-message form-message--error" role="alert">{profileError}</p>}{profileMessage && <p className="form-message form-message--success" role="status">{profileMessage}</p>}<button className="primary-button" type="submit">Actualizar contraseña</button></form><button className="text-button profile-logout" type="button" onClick={onLogout}><Icon name="logout" />Cerrar sesión</button></div>}</header>
}

function useLogout() {
  const navigate = useNavigate()
  return async () => {
    try {
      const refresh = obtenerRefreshToken()
      if (refresh) await cerrarSesion(refresh)
    } finally {
      cerrarSesionLocal()
      navigate('/', { replace: true })
    }
  }
}

function Login() {
  const navigate = useNavigate()
  const [setupMode, setSetupMode] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [setupToken, setSetupToken] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [estado, setEstado] = useState('idle')
  const [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault()
    if (!username.trim() || !password) return setError('Escribe tu nombre de usuario y contraseña para continuar.')
    setEstado('loading'); setError('')
    try {
      if (setupMode) {
        await configurarAdministradorInicial({
          username: username.trim(),
          email: email.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          password,
          password_confirmation: passwordConfirmation,
          setup_token: setupToken,
        })
        setSetupMode(false)
        setPassword('')
        setPasswordConfirmation('')
        setSetupToken('')
        setError('Administrador creado. Ya puedes iniciar sesión.')
      } else {
        await iniciarSesion({ username: username.trim(), password })
        navigate('/inicio', { replace: true })
      }
      setEstado('idle')
    }
    catch (e) { setEstado('error'); setError(e.message) }
  }
  return <main className="login-page">
    <section className="login-intro" aria-labelledby="intro-title">
      <div className="brand-mark" aria-label="Simulador TyT"><span className="brand-mark__line" /><span>TyT</span></div>
      <div className="intro-copy"><p className="eyebrow">Plataforma de evaluación</p><h1 id="intro-title">Evaluar con claridad.</h1><p>Un espacio sereno para preparar, responder y revisar tus cuestionarios.</p></div>
      <p className="intro-note">Resultados que ayudan a avanzar.</p>
    </section>
    <section className="login-panel" aria-labelledby="login-title"><div className="login-panel__content">
      <header className="login-header"><p className="eyebrow">{setupMode ? 'Instalación inicial' : 'Acceso seguro'}</p><h2 id="login-title">{setupMode ? 'Configurar administrador' : 'Iniciar sesión'}</h2><p>{setupMode ? 'Crea la cuenta con control total de la plataforma.' : 'Ingresa con la cuenta que te entregó tu institución.'}</p></header>
      <form className="login-form" onSubmit={submit} noValidate>
        <div className="field"><label htmlFor="username">Nombre de usuario</label><input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} disabled={estado === 'loading'} autoFocus /></div>
        {setupMode && <><div className="field"><label htmlFor="first-name">Nombre</label><input id="first-name" autoComplete="given-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} disabled={estado === 'loading'} /></div><div className="field"><label htmlFor="last-name">Apellido</label><input id="last-name" autoComplete="family-name" value={lastName} onChange={(e) => setLastName(e.target.value)} disabled={estado === 'loading'} /></div><div className="field"><label htmlFor="email">Correo electrónico</label><input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={estado === 'loading'} /></div><div className="field"><label htmlFor="setup-token">Token de instalación</label><input id="setup-token" type="password" autoComplete="off" value={setupToken} onChange={(e) => setSetupToken(e.target.value)} disabled={estado === 'loading'} /></div></>}
        <div className="field"><label htmlFor="password">Contraseña</label><div className="password-field"><input id="password" type={mostrar ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={estado === 'loading'} /><button className="password-toggle" type="button" onClick={() => setMostrar(!mostrar)} aria-label={mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña'}>{mostrar ? 'Ocultar' : 'Mostrar'}</button></div></div>
        {setupMode && <div className="field"><label htmlFor="password-confirmation">Confirmar contraseña</label><input id="password-confirmation" type={mostrar ? 'text' : 'password'} autoComplete="new-password" value={passwordConfirmation} onChange={(e) => setPasswordConfirmation(e.target.value)} disabled={estado === 'loading'} /></div>}
        {error && <p className="form-message form-message--error" role="alert"><span aria-hidden="true">!</span>{error}</p>}
        <button className="primary-button" type="submit" disabled={estado === 'loading'}>{estado === 'loading' ? 'Procesando…' : setupMode ? 'Crear administrador' : 'Iniciar sesión'}</button>
      </form>
      <p className="login-footnote">{setupMode ? 'Este formulario solo funciona durante la instalación inicial.' : 'Si no tienes un administrador configurado, puedes iniciar la instalación.'} <button className="text-button" type="button" onClick={() => { setSetupMode(!setupMode); setError(''); setEstado('idle') }}>{setupMode ? 'Volver al inicio de sesión' : 'Configurar administrador inicial'}</button></p>
    </div></section>
  </main>
}

function Home() {
  const navigate = useNavigate()
  const logout = useLogout()
  const [cuestionarios, setCuestionarios] = useState([])
  const [intentos, setIntentos] = useState([])
  const [user, setUser] = useState(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('todos')
  const [estado, setEstado] = useState('loading')
  const [error, setError] = useState('')
  const [seleccionado, setSeleccionado] = useState(null)
  const [iniciando, setIniciando] = useState(false)
  const [claveEvaluacion, setClaveEvaluacion] = useState('')
  useEffect(() => {
    api.obtenerMe().then((currentUser) => {
      setUser(currentUser)
      const requests = [obtenerCuestionariosDisponibles()]
      if (currentUser.roles?.includes('Estudiante')) requests.push(api.obtenerIntentos())
      return Promise.all(requests)
    }).then(([d, i = []]) => {
      setCuestionarios(d)
      setIntentos(i)
      setEstado('success')
    }).catch((e) => { setError(e.message); setEstado('error') })
  }, [])
  const visibles = cuestionarios.filter((q) => {
    const matchesSearch = q.nombre.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'todos' || (filter === 'cerrados' && q.fecha_cierre && new Date(q.fecha_cierre) < new Date()) || (filter === 'sin-intentos' && !q.puede_iniciar)
    return matchesSearch && matchesFilter
  })
  async function start() {
    setIniciando(true)
    try { const data = await iniciarIntento(seleccionado.id, claveEvaluacion); navigate(`/intentos/${data.intento_id}`) }
    catch (e) { setError(e.message) }
    finally { setIniciando(false) }
  }
  return <main className="app-shell"><Topbar onLogout={logout}><button className="text-button" type="button" onClick={() => navigate('/inicio')}><Icon name="quiz" />Cuestionarios</button><button className="text-button" type="button" onClick={() => navigate('/gestion')}><Icon name="settings" />Gestión</button></Topbar>
    <section className="content-column" aria-labelledby="available-title"><header className="page-heading"><p className="eyebrow">Estudiante</p><h1 id="available-title">Cuestionarios disponibles</h1><p>Elige una evaluación cuando estés listo para comenzar.</p></header>
      {estado === 'loading' && <div className="state-block" role="status"><span className="loading-dot" aria-hidden="true" /><p>Consultando cuestionarios disponibles…</p></div>}
      {estado === 'error' && <div className="state-block state-block--error" role="alert"><p>{error}</p><button className="secondary-button" type="button" onClick={() => window.location.reload()}>Intentar de nuevo</button></div>}
      {estado === 'success' && <><div className="quiz-filters"><input aria-label="Buscar cuestionario" placeholder="Buscar por nombre" value={search} onChange={(e) => setSearch(e.target.value)} /><select aria-label="Filtrar cuestionarios" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="todos">Todos</option><option value="cerrados">Ya cerraron</option><option value="sin-intentos">No permiten más intentos</option></select></div>{!visibles.length && <div className="empty-state"><p className="eyebrow">Sin coincidencias</p><h2>No hay cuestionarios para este filtro.</h2></div>}<div className="quiz-list">{visibles.map((q) => <article className={q.puede_iniciar ? 'quiz-row' : 'quiz-row quiz-row--blocked'} key={q.id}><div className="quiz-row__content"><h2>{q.nombre}</h2><p className="quiz-status">{q.puede_iniciar ? 'Disponible para resolver' : q.motivo_bloqueo}</p><dl className="quiz-meta"><div><dt>Preguntas</dt><dd>{q.total_preguntas}</dd></div><div><dt>Intentos</dt><dd>{q.intentos_realizados} / {q.max_intentos}</dd></div><div><dt>Cierra</dt><dd>{q.fecha_cierre ? dateFormatter.format(new Date(q.fecha_cierre)) : 'Sin fecha'}</dd></div></dl></div><button className="primary-button quiz-row__action" type="button" onClick={() => setSeleccionado(q)} disabled={!q.puede_iniciar}>Iniciar intento</button></article>)}</div>      <section className={user?.roles?.includes('Estudiante') ? 'student-results' : 'student-results student-results--hidden'}><div className="section-heading"><div><p className="eyebrow">Seguimiento</p><h2>Mis resultados e intentos</h2></div></div>{!intentos.length ? <p>Aún no tienes intentos registrados.</p> : <div className="data-list">{intentos.map((item) => <article className="data-row" key={item.id}><div><h3>{item.cuestionario_nombre}</h3><p>{shortDate.format(new Date(item.fecha_inicio))} · {item.estado === 'EN_CURSO' ? 'En curso' : item.resultado_publicado ? `Calificación: ${item.calificacion_final} / ${item.nota_maxima}` : 'Resultado pendiente'}</p></div>{item.enviado ? <button className="secondary-button" onClick={() => navigate(`/resultados/${item.id}`)}>Ver resultado</button> : <button className="secondary-button" onClick={() => navigate(`/intentos/${item.id}`)}>Continuar</button>}</article>)}</div>}</section></>}
    </section>
    {seleccionado && <div className="dialog-backdrop"><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><p className="eyebrow">Antes de comenzar</p><h2 id="confirm-title">{seleccionado.nombre}</h2><p>Al continuar comenzará uno de tus intentos. Guarda tus respuestas antes de finalizar.</p>{seleccionado.requiere_contrasena && <label className="field">Contraseña de acceso<input type="password" autoComplete="off" value={claveEvaluacion} onChange={(event) => setClaveEvaluacion(event.target.value)} /></label>}{error && <p className="form-message form-message--error" role="alert">{error}</p>}<div className="dialog-summary"><span>{seleccionado.total_preguntas} preguntas</span><span>{seleccionado.duracion_minutos ? `${seleccionado.duracion_minutos} minutos` : 'Sin límite de tiempo'}</span></div><div className="dialog-actions"><button className="secondary-button" type="button" onClick={() => { setSeleccionado(null); setClaveEvaluacion(''); setError('') }} disabled={iniciando}>Volver</button><button className="primary-button" type="button" onClick={start} disabled={iniciando || (seleccionado.requiere_contrasena && !claveEvaluacion)}>{iniciando ? 'Iniciando…' : 'Comenzar ahora'}</button></div></section></div>}
  </main>
}

function AttemptPage() {
  const id = useLocation().pathname.split('/').pop()
  const navigate = useNavigate()
  const logout = useLogout()
  const [attempt, setAttempt] = useState(null)
  const [index, setIndex] = useState(0)
  const [estado, setEstado] = useState('loading')
  const [guardando, setGuardando] = useState(false)
  const [confirmingSubmit, setConfirmingSubmit] = useState(false)
  const [error, setError] = useState('')
  const [remaining, setRemaining] = useState(null)
  useEffect(() => { api.obtenerIntento(id).then((data) => { if (data.enviado) { navigate(`/resultados/${id}`, { replace: true }); return } setAttempt(data); setEstado('ready') }).catch((e) => { setError(e.message); setEstado('error') }) }, [id, navigate])
  useEffect(() => {
    if (!attempt?.fecha_inicio || !attempt.preguntas) return undefined
    if (!attempt.fecha_limite) return undefined
    const tick = () => setRemaining(Math.max(0, Math.floor((new Date(attempt.fecha_limite).getTime() - Date.now()) / 1000)))
    tick(); const timer = setInterval(tick, 1000); return () => clearInterval(timer)
  }, [attempt])
  useEffect(() => {
    if (remaining !== 0 || !attempt) return
    api.obtenerIntento(id).then(() => navigate(`/resultados/${id}`, { replace: true })).catch((e) => setError(e.message))
  }, [remaining, attempt, id, navigate])
  useEffect(() => { const warn = (e) => { if (attempt && !attempt.enviado) { e.preventDefault(); e.returnValue = '' } }; window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn) }, [attempt])
  const answers = useMemo(() => Object.fromEntries((attempt?.respuestas || []).map((r) => [r.pregunta, r.opcion])), [attempt])
  const reviewFlags = useMemo(() => Object.fromEntries((attempt?.respuestas || []).map((r) => [r.pregunta, r.marcada_revision])), [attempt])
  const question = attempt?.preguntas?.[index]
  async function choose(option) {
    setGuardando(true); setError('')
    try { await api.guardarRespuesta(id, { pregunta: question.id, opcion: option }); setAttempt((a) => ({ ...a, respuestas: a.respuestas.map((r) => r.pregunta === question.id ? { ...r, opcion: option, opcion_texto: question.opciones.find((o) => o.id === option)?.texto } : r), preguntas_sin_responder: a.respuestas.filter((r) => r.pregunta !== question.id && !r.opcion).length })) }
    catch (e) { setError(e.message) } finally { setGuardando(false) }
  }
  async function toggleReview() {
    const marcada_revision = !reviewFlags[question.id]
    setGuardando(true); setError('')
    try {
      await api.marcarRespuesta(id, question.id, marcada_revision)
      setAttempt((a) => ({ ...a, respuestas: a.respuestas.map((r) => r.pregunta === question.id ? { ...r, marcada_revision } : r) }))
    } catch (e) { setError(e.message) } finally { setGuardando(false) }
  }
  async function submit() {
    setConfirmingSubmit(true)
  }
  async function confirmSubmit() {
    setConfirmingSubmit(false)
    try { const result = await api.enviarIntento(id); navigate(`/resultados/${id}`, { state: { result } }) } catch (e) { setError(e.message) }
  }
  if (estado === 'loading') return <LoadingScreen text="Cargando tu intento…" />
  if (estado === 'error') return <ErrorScreen error={error} onBack={() => navigate('/inicio')} />
  if (!question) return <ErrorScreen error="Este intento no contiene preguntas disponibles." onBack={() => navigate('/inicio')} />
  const minutes = remaining === null ? null : Math.floor(remaining / 60)
  const seconds = remaining === null ? null : String(remaining % 60).padStart(2, '0')
  return <main className="app-shell attempt-page"><Topbar title={attempt.cuestionario_nombre} onLogout={logout}><span className={remaining !== null && remaining < 60 ? 'timer timer--urgent' : 'timer'}>{remaining === null ? 'Sin límite' : `${minutes}:${seconds}`}</span></Topbar>
    <section className="content-column attempt-content"><div className="attempt-header"><div><p className="eyebrow">Pregunta {index + 1} de {attempt.preguntas.length}</p><h1>{attempt.cuestionario_nombre}</h1></div><span className="save-status" role="status">{guardando ? 'Guardando…' : 'Progreso guardado'}</span></div>
      {error && <p className="form-message form-message--error" role="alert"><span aria-hidden="true">!</span>{error}</p>}
      <div className="progress-track" aria-label={`Progreso: ${index + 1} de ${attempt.preguntas.length}`}><span style={{ width: `${((index + 1) / attempt.preguntas.length) * 100}%` }} /></div>
      <article className="question-panel"><p className="question-type">{question.tipo === 'VF' ? 'Verdadero o falso' : 'Selección única'}</p>{question.texto_base && <p className="base-text">{question.texto_base}</p>}<h2>{question.enunciado}</h2><fieldset><legend className="sr-only">Opciones de respuesta</legend>{question.opciones.map((option) => <label className={answers[question.id] === option.id ? 'option-card option-card--selected' : 'option-card'} key={option.id}><input type="radio" name={`question-${question.id}`} checked={answers[question.id] === option.id} onChange={() => choose(option.id)} disabled={guardando} /><span>{option.texto}</span></label>)}</fieldset><button className={reviewFlags[question.id] ? 'review-toggle review-toggle--active' : 'review-toggle'} type="button" onClick={toggleReview} disabled={guardando}>⚑ {reviewFlags[question.id] ? 'Marcada para revisar' : 'Marcar para revisar'}</button></article>
      <nav className="question-navigation" aria-label="Navegación de preguntas"><button className="secondary-button" type="button" onClick={() => setIndex(Math.max(0, index - 1))} disabled={index === 0}>Anterior</button><span>{attempt.preguntas_sin_responder} sin responder</span>{index < attempt.preguntas.length - 1 ? <button className="primary-button" type="button" onClick={() => setIndex(index + 1)}>Siguiente</button> : <button className="primary-button" type="button" onClick={submit}>Finalizar intento</button>}</nav>
    </section>{confirmingSubmit && <div className="dialog-backdrop" role="presentation"><section className="confirm-dialog submit-dialog" role="dialog" aria-modal="true" aria-labelledby="submit-title"><div className="submit-dialog__icon" aria-hidden="true">✓</div><p className="eyebrow">Confirmar entrega</p><h2 id="submit-title">¿Deseas finalizar este intento?</h2><p>Al enviar se guardarán tus respuestas actuales y ya no podrás modificarlas.</p><div className="dialog-summary"><span>{attempt.preguntas_sin_responder} preguntas sin responder</span><span>{attempt.preguntas.length - attempt.preguntas_sin_responder} respondidas</span></div><div className="dialog-actions"><button className="secondary-button" type="button" onClick={() => setConfirmingSubmit(false)}>Continuar resolviendo</button><button className="primary-button" type="button" onClick={confirmSubmit}>Finalizar intento</button></div></section></div>}</main>
}

function ResultPage() {
  const id = useLocation().pathname.split('/').pop()
  const navigate = useNavigate(); const logout = useLogout()
  const [data, setData] = useState(null); const [revision, setRevision] = useState(null); const [error, setError] = useState('')
  useEffect(() => { api.obtenerIntento(id).then(setData).catch((e) => setError(e.message)) }, [id])
  async function showRevision() { try { setRevision(await api.obtenerRevision(id)) } catch (e) { setError(e.message) } }
  if (error) return <ErrorScreen error={error} onBack={() => navigate('/inicio')} />
  if (!data) return <LoadingScreen text="Calculando tu resultado…" />
  if (!data.resultado_publicado) return <main className="app-shell"><Topbar title="Entrega registrada" onLogout={logout}><button className="text-button" type="button" onClick={() => navigate('/inicio')}>Cuestionarios</button></Topbar><section className="content-column result-page"><p className="eyebrow">Intento finalizado</p><h1>{data.cuestionario_nombre}</h1><div className="empty-state"><h2>Entrega registrada</h2><p>El docente publicará el resultado cuando esté disponible.</p></div><p>Estado: {data.estado === 'VENCIDO' ? 'Vencido por tiempo' : 'Enviado'}</p></section></main>
  return <main className="app-shell"><Topbar title="Resultado" onLogout={logout}><button className="text-button" type="button" onClick={() => navigate('/inicio')}>Cuestionarios</button></Topbar><section className="content-column result-page"><p className="eyebrow">Intento finalizado</p><h1>{data.cuestionario_nombre}</h1><div className={data.aprobado ? 'score-card score-card--pass' : 'score-card'}><span>Calificación final</span><strong>{data.calificacion_final} <small>/ {data.nota_maxima}</small></strong><b>{data.aprobado ? 'Aprobado' : 'No aprobado'}</b></div><dl className="result-details"><div><dt>Estado</dt><dd>{data.estado === 'VENCIDO' ? 'Vencido por tiempo' : 'Enviado'}</dd></div><div><dt>Sin responder</dt><dd>{data.preguntas_sin_responder}</dd></div><div><dt>Nota para aprobar</dt><dd>{data.nota_aprobar}</dd></div></dl>{data.revision_habilitada !== false && <button className="secondary-button" type="button" onClick={showRevision}>Ver revisión</button>}{revision && <div className="revision-list">{revision.map((item, i) => <article key={item.pregunta}><p className="eyebrow">Pregunta {i + 1}</p><h2>{item.pregunta_enunciado}</h2><p className={item.opcion === item.opcion_correcta ? 'answer answer--correct' : 'answer answer--wrong'}>{item.opcion_texto || 'Sin respuesta'}</p>{item.retroalimentacion && <p className="feedback">{item.retroalimentacion}</p>}</article>)}</div>}</section></main>
}

function ManagementPage() {
  const navigate = useNavigate(); const logout = useLogout()
  const [me, setMe] = useState(null); const [tab, setTab] = useState('preguntas')
  useEffect(() => { api.obtenerMe().then(setMe).catch(() => navigate('/inicio')) }, [navigate])
  const can = (permission) => me?.permissions?.includes('*') || me?.permissions?.includes(permission)
  const isStudent = me?.roles?.includes('Estudiante')
  const canManage = me?.is_staff || me?.permissions?.length || isStudent
  const canManageQuestions = can('manage_question_bank')
  const tabs = [
    ...(isStudent ? [['seguimiento', 'Mi seguimiento', 'results']] : []),
    ...(canManageQuestions ? [['preguntas', 'Banco de preguntas', 'questions'], ['catalogos', 'Categorías y competencias', 'catalog'], ['importar', 'Importar preguntas', 'upload']] : []),
    ...(can('configure_quizzes') ? [['cuestionarios', 'Cuestionarios', 'quiz']] : []),
    ...(can('ver_reportes') ? [['reportes', 'Consultas y reportes', 'reports']] : []),
    ...(can('view_results') ? [['resultados', 'Resultados', 'results']] : []),
    ...(can('manage_users') ? [['usuarios', 'Usuarios', 'user']] : []),
    ...(can('manage_roles') ? [['roles', 'Roles', 'roles']] : []),
  ]
  useEffect(() => { if (me && !tabs.some(([value]) => value === tab)) setTab(tabs[0]?.[0] || '') }, [me, tab, tabs])
  if (!me) return <LoadingScreen text="Cargando permisos…" />
  if (!canManage) return <ErrorScreen error="No tienes permisos para acceder a la gestión." onBack={() => navigate('/inicio')} />
  if (!tabs.length) return <ErrorScreen error="Tu cuenta no tiene permisos de gestión asignados." onBack={() => navigate('/inicio')} />
  return <main className="app-shell"><Topbar title="Gestión" onLogout={logout}><button className="text-button" type="button" onClick={() => navigate('/inicio')}><Icon name="quiz" />Cuestionarios</button></Topbar><section className="content-column management"><header className="page-heading"><p className="eyebrow">{isStudent ? 'Estudiante' : 'Administración'}</p><h1>{isStudent ? 'Mi seguimiento académico' : 'Gestionar la plataforma'}</h1><p>{isStudent ? 'Consulta tus intentos y resultados sin acceder a módulos administrativos.' : 'Administra preguntas, evaluaciones, usuarios, roles, resultados y reportes.'}</p></header><nav className="segment-control" aria-label="Secciones de gestión">{tabs.map(([value, label, icon]) => <button key={value} className={tab === value ? 'segment-control__item segment-control__item--active' : 'segment-control__item'} onClick={() => setTab(value)} type="button"><Icon name={icon} />{label}</button>)}</nav>{tab === 'seguimiento' && <StudentTracking />}{tab === 'preguntas' && <QuestionManager />}{tab === 'catalogos' && <CatalogManager />}{tab === 'cuestionarios' && <QuizManager />}{tab === 'resultados' && <ResultsManager />}{tab === 'reportes' && <Reportes canSeeIdentification={can('ver_identificacion_estudiante')} isStudent={!can('ver_reportes')} />}{tab === 'usuarios' && <UserManager />}{tab === 'roles' && <RoleManager />}{tab === 'importar' && <ImportManager />}</section></main>
}

function StudentTracking() {
  const navigate = useNavigate()
  const [intentos, setIntentos] = useState([])
  const [error, setError] = useState('')
  useEffect(() => { api.obtenerIntentos().then(setIntentos).catch((e) => setError(e.message)) }, [])
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Resultados e intentos</p><h2>Mi historial</h2></div></div>{error && <p className="form-message form-message--error" role="alert">{error}</p>}{!error && !intentos.length && <div className="empty-state"><h2>Aún no tienes intentos registrados.</h2><p>Cuando resuelvas un cuestionario, aquí podrás consultar su estado y resultado.</p></div>}{!!intentos.length && <div className="data-list">{intentos.map((item) => <article className="data-row" key={item.id}><div><h3>{item.cuestionario_nombre}</h3><p>{shortDate.format(new Date(item.fecha_inicio))} · {item.estado === 'EN_CURSO' ? 'En curso' : item.resultado_publicado ? `Calificación: ${item.calificacion_final} / ${item.nota_maxima}` : 'Resultado pendiente'}</p></div>{item.enviado ? <button className="secondary-button" onClick={() => navigate(`/resultados/${item.id}`)}>Ver resultado</button> : <button className="secondary-button" onClick={() => navigate(`/intentos/${item.id}`)}>Continuar</button>}</article>)}</div>}</section>
}

function CatalogManager() {
  const [categories, setCategories] = useState([]); const [competencies, setCompetencies] = useState([]); const [categoryName, setCategoryName] = useState(''); const [competencyName, setCompetencyName] = useState(''); const [error, setError] = useState(''); const [saving, setSaving] = useState(false)
  const load = () => Promise.all([api.obtenerCategorias(), api.obtenerCompetencias()]).then(([cats, comps]) => { setCategories(cats); setCompetencies(comps) }).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  async function save(kind) {
    const name = kind === 'category' ? categoryName.trim() : competencyName.trim()
    if (!name) return
    setSaving(true); setError('')
    try { if (kind === 'category') { await api.guardarCategoria({ nombre: name }); setCategoryName('') } else { await api.guardarCompetencia({ nombre: name }); setCompetencyName('') }; load() }
    catch (e) { setError(e.message) } finally { setSaving(false) }
  }
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Catálogos del banco</p><h2>Categorías y competencias</h2></div></div><p className="section-intro">Solo las personas con el permiso de administrar el banco de preguntas pueden crear o editar estos catálogos.</p>{error && <p className="form-message form-message--error" role="alert">{error}</p>}<div className="catalog-grid"><div className="catalog-column"><h3>Categorías</h3><div className="inline-form"><label className="sr-only" htmlFor="new-category">Nueva categoría</label><input id="new-category" value={categoryName} onChange={(e) => setCategoryName(e.target.value)} placeholder="Ej. Lectura crítica" /><button className="primary-button" type="button" onClick={() => save('category')} disabled={saving || !categoryName.trim()}>Crear</button></div><div className="data-list">{categories.map((item) => <div className="catalog-item" key={item.id}>{item.nombre}</div>)}</div></div><div className="catalog-column"><h3>Competencias</h3><div className="inline-form"><label className="sr-only" htmlFor="new-competency">Nueva competencia</label><input id="new-competency" value={competencyName} onChange={(e) => setCompetencyName(e.target.value)} placeholder="Ej. Interpretación" /><button className="primary-button" type="button" onClick={() => save('competency')} disabled={saving || !competencyName.trim()}>Crear</button></div><div className="data-list">{competencies.map((item) => <div className="catalog-item" key={item.id}>{item.nombre}</div>)}</div></div></div></section>
}

function ResultsManager() {
  const [quizzes, setQuizzes] = useState([]); const [selected, setSelected] = useState(''); const [data, setData] = useState(null); const [error, setError] = useState('')
  useEffect(() => { api.obtenerCuestionarios().then((rows) => { setQuizzes(rows); if (rows.length) setSelected(String(rows[0].id)) }).catch((e) => setError(e.message)) }, [])
  useEffect(() => { if (selected) api.obtenerResultadosCuestionario(selected).then(setData).catch((e) => { setData(null); setError(e.message) }) }, [selected])
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Seguimiento</p><h2>Resultados por evaluación</h2></div></div><label className="field">Cuestionario<select value={selected} onChange={(event) => { setSelected(event.target.value); setError('') }}><option value="">Selecciona una evaluación</option>{quizzes.map((quiz) => <option key={quiz.id} value={quiz.id}>{quiz.nombre}</option>)}</select></label>{error && <p className="form-message form-message--error" role="alert">{error}</p>}{data && <><div className="report-indicators">{[['Participantes', data.indicadores.participantes], ['Intentos finalizados', data.indicadores.intentos_finalizados], ['Aprobados', data.indicadores.aprobados], ['Reprobados', data.indicadores.reprobados], ['Promedio', data.indicadores.promedio == null ? '—' : Number(data.indicadores.promedio).toFixed(2)]].map(([label, value]) => <article className="report-indicator" key={label}><span>{label}</span><strong>{value}</strong></article>)}</div><h3>Distribución de calificaciones</h3><div className="data-list">{data.distribucion.map((item) => <article className="data-row" key={item.rango}><span>{item.rango}</span><strong>{item.cantidad}</strong></article>)}</div><h3>Intentos de estudiantes</h3><div className="report-table-wrap"><table className="report-table"><thead><tr><th>Estudiante</th><th>Estado</th><th>Entrega</th><th>Calificación</th><th>Resultado</th></tr></thead><tbody>{data.intentos.map((item) => <tr key={item.intento_id}><td>{item.estudiante}</td><td>{item.estado}</td><td>{item.fecha_envio ? dateFormatter.format(new Date(item.fecha_envio)) : '—'}</td><td>{item.calificacion ?? '—'}</td><td>{item.aprobado == null ? '—' : item.aprobado ? 'Aprobado' : 'Reprobado'}</td></tr>)}</tbody></table></div><h3>Aciertos por pregunta</h3><div className="report-table-wrap"><table className="report-table"><thead><tr><th>Pregunta</th><th>Eje</th><th>Respuestas</th><th>Aciertos</th><th>Errores</th><th>% aciertos</th></tr></thead><tbody>{data.preguntas.map((item) => <tr key={item.pregunta_id}><td>{item.enunciado}</td><td>{item.eje || '—'}</td><td>{item.respuestas}</td><td>{item.aciertos}</td><td>{item.errores}</td><td>{item.porcentaje_aciertos}%</td></tr>)}</tbody></table></div><h3>Desempeño por eje temático</h3>{data.eje_mayor_acierto && <p>Mayor porcentaje: {data.eje_mayor_acierto.eje} ({data.eje_mayor_acierto.porcentaje_aciertos}%). Mayor dificultad: {data.eje_mas_dificil.eje} ({data.eje_mas_dificil.porcentaje_aciertos}% de aciertos).</p>}<div className="report-table-wrap"><table className="report-table"><thead><tr><th>Eje</th><th>Respuestas</th><th>Aciertos</th><th>Errores</th><th>% aciertos</th></tr></thead><tbody>{data.ejes.map((item) => <tr key={item.eje}><td>{item.eje}</td><td>{item.respuestas}</td><td>{item.aciertos}</td><td>{item.errores}</td><td>{item.porcentaje_aciertos}%</td></tr>)}</tbody></table></div></>}</section>
}

function QuestionManager() {
  const [items, setItems] = useState([]); const [categories, setCategories] = useState([]); const [competencies, setCompetencies] = useState([]); const [editing, setEditing] = useState(null); const [error, setError] = useState('')
  const load = () => Promise.all([api.obtenerPreguntas(), api.obtenerCategorias(), api.obtenerCompetencias()]).then(([q, c, k]) => { setItems(q); setCategories(c); setCompetencies(k) }).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  async function toggle(item) { try { await api.cambiarEstadoPregunta(item.id, !item.activa); load() } catch (e) { setError(e.message) } }
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Banco de preguntas</p><h2>Preguntas registradas</h2></div><button className="primary-button" onClick={() => setEditing({ tipo: 'UNICA', puntaje: '1', opciones: [{ texto: '', es_correcta: true, orden: 1 }, { texto: '', es_correcta: false, orden: 2 }] })}>Nueva pregunta</button></div>{error && <p className="form-message form-message--error" role="alert">{error}</p>}{editing && <QuestionForm initial={editing} categories={categories} competencies={competencies} onDone={() => { setEditing(null); load() }} />}{!editing && <div className="data-list">{items.map((item) => <article className="data-row" key={item.id}><div><h3>{item.enunciado}</h3><p>{item.categoria_nombre || 'Sin categoría'} · {item.tipo} · {item.puntaje} puntos</p></div><div className="row-actions"><span className={item.activa ? 'status status--active' : 'status'}>{item.activa ? 'Activa' : 'Inactiva'}</span><button className="text-button" onClick={() => api.obtenerPregunta(item.id).then(setEditing)}>Editar</button><button className="text-button" onClick={() => toggle(item)}>{item.activa ? 'Desactivar' : 'Activar'}</button></div></article>)}</div>}</section>
}

function QuestionForm({ initial, categories, competencies, onDone }) {
  const [form, setForm] = useState(initial); const [error, setError] = useState(''); const set = (key, value) => setForm((f) => ({ ...f, [key]: value }))
  function option(index, key, value) { set('opciones', form.opciones.map((o, i) => i === index ? { ...o, [key]: value } : o)) }
  async function submit(e) { e.preventDefault(); try { await api.guardarPregunta({ ...form, puntaje: Number(form.puntaje), categoria: form.categoria || null, competencia: form.competencia || null, opciones: form.opciones.map((o, i) => ({ ...o, orden: i + 1 })) }, form.id); onDone() } catch (x) { setError(x.message) } }
  return <form className="editor-form" onSubmit={submit}><div className="form-grid"><div className="field"><label htmlFor="enunciado">Enunciado</label><textarea id="enunciado" required value={form.enunciado || ''} onChange={(e) => set('enunciado', e.target.value)} /></div><div className="field"><label htmlFor="texto_base">Texto base</label><textarea id="texto_base" value={form.texto_base || ''} onChange={(e) => set('texto_base', e.target.value)} /></div><div className="field"><label htmlFor="tipo">Tipo</label><select id="tipo" value={form.tipo} onChange={(e) => { const tipo = e.target.value; setForm((f) => ({ ...f, tipo, opciones: tipo === 'VF' ? [{ texto: 'Verdadero', es_correcta: true, orden: 1 }, { texto: 'Falso', es_correcta: false, orden: 2 }] : f.opciones })) }}><option value="UNICA">Opción única</option><option value="MULTIPLE">Selección con una respuesta</option><option value="VF">Verdadero o falso</option></select></div><div className="field"><label htmlFor="puntaje">Puntaje</label><input id="puntaje" type="number" min="0.01" step="0.01" value={form.puntaje} onChange={(e) => set('puntaje', e.target.value)} /></div><div className="field"><label htmlFor="categoria">Categoría (obligatoria)</label><select id="categoria" required value={form.categoria || ''} onChange={(e) => set('categoria', e.target.value)}><option value="">Selecciona una categoría</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select></div><div className="field"><label htmlFor="competencia">Competencia</label><select id="competencia" value={form.competencia || ''} onChange={(e) => set('competencia', e.target.value)}><option value="">Sin competencia</option>{competencies.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select></div></div><fieldset className="options-editor"><legend>Opciones y respuesta correcta</legend>{form.opciones.map((o, i) => <div className="option-edit" key={i}><input required value={o.texto} aria-label={`Opción ${i + 1}`} onChange={(e) => option(i, 'texto', e.target.value)} /><label><input type="radio" name="correcta" checked={o.es_correcta} onChange={() => set('opciones', form.opciones.map((x, n) => ({ ...x, es_correcta: n === i })))} /> Correcta</label></div>)}</fieldset>{error && <p className="form-message form-message--error">{error}</p>}<div className="dialog-actions"><button className="secondary-button" type="button" onClick={onDone}>Cancelar</button><button className="primary-button" type="submit">Guardar pregunta</button></div></form>
}

function QuizManager() {
  const [items, setItems] = useState([]); const [questions, setQuestions] = useState([]); const [courses, setCourses] = useState([]); const [editing, setEditing] = useState(null); const [error, setError] = useState('')
  const load = () => Promise.all([api.obtenerCuestionarios(), api.obtenerPreguntas('?activa=true'), api.obtenerCursosAcademicos()]).then(([q, p, c]) => { setItems(q); setQuestions(p); setCourses(c) }).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  async function toggle(item) { try { await api.cambiarEstadoCuestionario(item.id, !item.activo); load() } catch (e) { setError(e.message) } }
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Evaluaciones</p><h2>Cuestionarios configurados</h2></div><button className="primary-button" onClick={() => setEditing({ nombre: '', descripcion: '', tematica: '', curso: '', fecha_apertura: '', fecha_cierre: '', duracion_minutos: 60, max_intentos: 1, nota_maxima: 5, nota_aprobar: 3, permitir_revision: true, publicar_resultado: true, estado: 'BORRADOR', activo: false, preguntas: [] })}>Nuevo cuestionario</button></div><p className="section-intro">Para crear uno, selecciona “Nuevo cuestionario”, completa sus fechas, curso, escala e intentos, y luego elige las preguntas activas del banco. Guárdalo inactivo mientras lo preparas y actívalo cuando esté listo.</p>{error && <p className="form-message form-message--error">{error}</p>}{editing && <QuizForm initial={editing} questions={questions} courses={courses} onDone={() => { setEditing(null); load() }} />}{!editing && <div className="data-list">{items.map((item) => <article className="data-row" key={item.id}><div><h3>{item.nombre}</h3><p>{item.total_preguntas} preguntas · Abre {item.fecha_apertura ? shortDate.format(new Date(item.fecha_apertura)) : 'Sin apertura'}</p></div><div className="row-actions"><span className={item.activo ? 'status status--active' : 'status'}>{item.estado === 'BORRADOR' ? 'Borrador' : item.activo ? 'Publicado' : 'Desactivado'}</span><button className="icon-button" onClick={() => api.obtenerCuestionario(item.id).then(setEditing)} aria-label={`Editar ${item.nombre}`} title="Editar"><Icon name="edit" /></button><button className="text-button" onClick={() => toggle(item)}>{item.activo ? 'Desactivar' : 'Activar'}</button></div></article>)}</div>}</section>
}

function QuizForm({ initial, questions, courses, onDone }) {
  const [form, setForm] = useState({ ...initial, fecha_apertura: initial.fecha_apertura?.slice(0, 16) || '', fecha_cierre: initial.fecha_cierre?.slice(0, 16) || '', preguntas: initial.preguntas || [], contrasena: '' })
  const [quitarContrasena, setQuitarContrasena] = useState(false)
  const [error, setError] = useState('')
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }))
  async function submit(e) {
    e.preventDefault()
    try {
      const payload = { ...form, curso: form.curso || null, preguntas: form.preguntas.map((p, i) => ({ pregunta: p.pregunta || p.id || p, orden: i + 1 })), duracion_minutos: Number(form.duracion_minutos), max_intentos: Number(form.max_intentos), nota_maxima: form.nota_maxima, nota_aprobar: form.nota_aprobar }
      if (!payload.contrasena && initial.requiere_contrasena && quitarContrasena) payload.contrasena = ''
      else if (!payload.contrasena) delete payload.contrasena
      await api.guardarCuestionario(payload, form.id)
      onDone()
    } catch (x) { setError(x.message) }
  }
  return <form className="editor-form" onSubmit={submit}>
    <div className="form-grid">
      <div className="field field--wide"><label htmlFor="quiz-name">Título</label><input id="quiz-name" required value={form.nombre} onChange={(e) => set('nombre', e.target.value)} /></div>
      <div className="field field--wide"><label htmlFor="quiz-description">Descripción</label><textarea id="quiz-description" value={form.descripcion || ''} onChange={(e) => set('descripcion', e.target.value)} /></div>
      <div className="field"><label htmlFor="quiz-topic">Asignatura o temática</label><input id="quiz-topic" value={form.tematica || ''} onChange={(e) => set('tematica', e.target.value)} /></div>
      <div className="field"><label htmlFor="quiz-course">Curso / grupo</label><select id="quiz-course" value={form.curso || ''} onChange={(e) => set('curso', e.target.value)}><option value="">Sin asignar</option>{courses.map((course) => <option key={course.id} value={course.id}>{course.nombre} · {course.periodo}</option>)}</select></div>
      <div className="field"><label htmlFor="open">Fecha de apertura</label><input id="open" type="datetime-local" required value={form.fecha_apertura} onChange={(e) => set('fecha_apertura', e.target.value)} /></div>
      <div className="field"><label htmlFor="close">Fecha de cierre</label><input id="close" type="datetime-local" required value={form.fecha_cierre} onChange={(e) => set('fecha_cierre', e.target.value)} /></div>
      <div className="field"><label>Duración (minutos)</label><input type="number" min="1" value={form.duracion_minutos} onChange={(e) => set('duracion_minutos', e.target.value)} /></div>
      <div className="field"><label>Intentos permitidos</label><input type="number" min="1" value={form.max_intentos} onChange={(e) => set('max_intentos', e.target.value)} /></div>
      <div className="field"><label>Calificación máxima</label><input type="number" min="0.01" step="0.01" value={form.nota_maxima} onChange={(e) => set('nota_maxima', e.target.value)} /></div>
      <div className="field"><label>Nota para aprobar</label><input type="number" min="0" step="0.01" value={form.nota_aprobar} onChange={(e) => set('nota_aprobar', e.target.value)} /></div>
      <div className="field"><label>Contraseña de acceso (opcional)</label><input type="password" autoComplete="new-password" value={form.contrasena} placeholder={initial.requiere_contrasena ? 'Deja vacío para mantenerla' : ''} onChange={(e) => set('contrasena', e.target.value)} /></div>
    </div>
    {initial.id && <p className="section-intro">Estado: {form.estado === 'PUBLICADO' ? 'Publicado' : 'Borrador'}</p>}
    <fieldset className="question-picker"><legend>Preguntas del cuestionario</legend>{questions.map((q) => <label key={q.id}><input type="checkbox" checked={form.preguntas.some((p) => (p.pregunta || p.id || p) === q.id)} onChange={(e) => set('preguntas', e.target.checked ? [...form.preguntas, { pregunta: q.id }] : form.preguntas.filter((p) => (p.pregunta || p.id || p) !== q.id))} />{q.enunciado}</label>)}</fieldset>
    <label className="check-field"><input type="checkbox" checked={form.permitir_revision} onChange={(e) => set('permitir_revision', e.target.checked)} /> Permitir revisión después de enviar</label>
    <label className="check-field"><input type="checkbox" checked={form.publicar_resultado} onChange={(e) => set('publicar_resultado', e.target.checked)} /> Mostrar calificación al estudiante al entregar</label>
    {initial.requiere_contrasena && <label className="check-field"><input type="checkbox" checked={quitarContrasena} onChange={(e) => setQuitarContrasena(e.target.checked)} /> Quitar contraseña de acceso</label>}
    {error && <p className="form-message form-message--error" role="alert">{error}</p>}
    <div className="dialog-actions"><button className="secondary-button" type="button" onClick={onDone}>Cancelar</button><button className="primary-button" type="submit">Guardar cuestionario</button></div>
  </form>
}

function UserManager() {
  const [items, setItems] = useState([]); const [roles, setRoles] = useState([]); const [editing, setEditing] = useState(null); const [registration, setRegistration] = useState(null); const [error, setError] = useState('')
  const load = () => Promise.all([api.obtenerUsuarios(), api.obtenerRoles()]).then(([u, r]) => { setItems(u); setRoles(r) }).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Personas</p><h2>Usuarios</h2></div><div className="row-actions"><button className="primary-button" onClick={() => setRegistration('student')}>Registrar estudiante</button><button className="secondary-button" onClick={() => setRegistration('teacher')}>Registrar docente</button></div></div>{error && <p className="form-message form-message--error">{error}</p>}{registration && <UserRegistration type={registration} onDone={() => { setRegistration(null); load() }} />}{editing && !registration && <UserForm initial={editing} roles={roles} onDone={() => { setEditing(null); load() }} />}{!editing && !registration && <div className="data-list">{items.map((u) => <article className="data-row" key={u.id}><div><h3>{u.first_name || u.last_name ? `${u.first_name} ${u.last_name}` : u.username}</h3>  <p>{u.email || 'Sin correo'} · {u.roles?.join(', ') || 'Sin rol'}{u.cursos?.length ? ` · Curso: ${u.cursos.join(', ')}` : ''}</p></div><div className="row-actions"><span className={u.is_active ? 'status status--active' : 'status'}>{u.is_active ? 'Activa' : 'Inactiva'}</span><button className="icon-button" onClick={() => setEditing(u)} aria-label={`Editar ${u.username}`} title="Editar"><Icon name="edit" /></button></div></article>)}</div>}</section>
}

function UserForm({ initial, roles, onDone }) {
  const [form, setForm] = useState({ ...initial, roles: initial.roles || [] }); const [error, setError] = useState(''); const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  async function submit(e) { e.preventDefault(); try { await api.guardarUsuario({ ...form, roles: form.roles, ...(form.password ? {} : { password: undefined }) }, form.id); onDone() } catch (x) { setError(x.message) } }
  return <form className="editor-form" onSubmit={submit}><div className="form-grid"><div className="field"><label>Usuario</label><input required value={form.username} onChange={(e) => set('username', e.target.value)} /></div><div className="field"><label>Correo</label><input type="email" value={form.email || ''} onChange={(e) => set('email', e.target.value)} /></div><div className="field"><label>Nombres</label><input value={form.first_name || ''} onChange={(e) => set('first_name', e.target.value)} /></div><div className="field"><label>Apellidos</label><input value={form.last_name || ''} onChange={(e) => set('last_name', e.target.value)} /></div><div className="field"><label>{form.id ? 'Nueva contraseña (opcional)' : 'Contraseña'}</label><input type="password" minLength="8" required={!form.id} value={form.password || ''} onChange={(e) => set('password', e.target.value)} /></div></div><fieldset className="question-picker"><legend>Roles</legend>{roles.map((r) => <label key={r.id}><input type="checkbox" checked={form.roles.includes(r.name)} onChange={(e) => set('roles', e.target.checked ? [...form.roles, r.name] : form.roles.filter((x) => x !== r.name))} />{r.name}</label>)}</fieldset><label className="check-field"><input type="checkbox" checked={form.is_active} onChange={(e) => set('is_active', e.target.checked)} /> Cuenta activa</label>{error && <p className="form-message form-message--error">{error}</p>}<div className="dialog-actions"><button className="secondary-button" type="button" onClick={onDone}>Cancelar</button><button className="primary-button" type="submit">Guardar usuario</button></div></form>
}

function RoleManager() {
  const [items, setItems] = useState([]); const [permissions, setPermissions] = useState([]); const [editing, setEditing] = useState(null); const [error, setError] = useState('')
  const load = () => Promise.all([api.obtenerRoles(), api.obtenerPermisos()]).then(([r, p]) => { setItems(r); setPermissions(p) }).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  async function remove(id) { if (window.confirm('¿Eliminar este rol?')) { try { await api.eliminarRol(id); load() } catch (e) { setError(e.message) } } }
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Accesos</p><h2>Roles configurables</h2></div><button className="primary-button" onClick={() => setEditing({ name: '', activo: true, permissions: [] })}>Nuevo rol</button></div>{error && <p className="form-message form-message--error">{error}</p>}{editing && <RoleForm initial={editing} permissions={permissions} onDone={() => { setEditing(null); load() }} />}{!editing && <div className="data-list">{items.map((r) => <article className="data-row" key={r.id}><div><h3>{r.name}</h3><p>{r.permissions.length} permisos configurados</p></div><div className="row-actions"><span className={r.activo ? 'status status--active' : 'status'}>{r.activo ? 'Activo' : 'Inactivo'}</span><button className="icon-button" onClick={() => setEditing(r)} aria-label={`Editar ${r.name}`} title="Editar"><Icon name="edit" /></button><button className="icon-button" onClick={() => remove(r.id)} aria-label={`Eliminar ${r.name}`} title="Eliminar">×</button></div></article>)}</div>}</section>
}

function RoleForm({ initial, permissions, onDone }) {
  const [form, setForm] = useState(initial); const [error, setError] = useState(''); const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  async function submit(e) { e.preventDefault(); try { await api.guardarRol(form, form.id); onDone() } catch (x) { setError(x.message) } }
  return <form className="editor-form" onSubmit={submit}><div className="field"><label htmlFor="role-name">Nombre del rol</label><input id="role-name" required value={form.name} onChange={(e) => set('name', e.target.value)} /></div><label className="check-field"><input type="checkbox" checked={form.activo} onChange={(e) => set('activo', e.target.checked)} /> Rol activo</label><fieldset className="question-picker"><legend>Permisos</legend>{permissions.map((p) => <label key={p.id}><input type="checkbox" checked={form.permissions.includes(p.id)} onChange={(e) => set('permissions', e.target.checked ? [...form.permissions, p.id] : form.permissions.filter((x) => x !== p.id))} />{p.name}</label>)}</fieldset>{error && <p className="form-message form-message--error">{error}</p>}<div className="dialog-actions"><button className="secondary-button" type="button" onClick={onDone}>Cancelar</button><button className="primary-button" type="submit">Guardar rol</button></div></form>
}

function ImportManager() {
  const [items, setItems] = useState([]); const [categories, setCategories] = useState([]); const [competencies, setCompetencies] = useState([]); const [quizzes, setQuizzes] = useState([]); const [quizId, setQuizId] = useState(''); const [preview, setPreview] = useState(null); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [loading, setLoading] = useState(false)
  const load = () => Promise.all([api.obtenerImportaciones(), api.obtenerCategorias(), api.obtenerCompetencias(), api.obtenerCuestionarios()]).then(([imports, cats, comps, quizRows]) => { setItems(imports); setCategories(cats); setCompetencies(comps); setQuizzes(quizRows.filter((quiz) => quiz.estado === 'BORRADOR')) }).catch((e) => setError(e.message)); useEffect(() => { load() }, [])
  async function previewFile(e) { const selected = e.target.files[0]; if (!selected) return; setLoading(true); setError(''); try { setPreview(await api.previsualizarImportacion(selected, quizId)) ; load() } catch (x) { setError(x.message) } finally { setLoading(false) } }
  async function revalidate() { setLoading(true); setError(''); try { setPreview(await api.actualizarImportacion(preview.importacion_id, preview.filas)) ; load() } catch (e) { setError(e.message) } finally { setLoading(false) } }
  async function confirm() { try { const result = await api.confirmarImportacion(preview.importacion_id); setNotice(result.preguntas_asignadas ? `${result.detail} ${result.preguntas_asignadas} preguntas quedaron vinculadas al cuestionario.` : result.detail); setPreview(null); load() } catch (e) { setError(e.message) } }
  function updateRow(index, key, value) { setPreview((current) => ({ ...current, filas: current.filas.map((row, i) => i === index ? { ...row, datos: { ...row.datos, [key]: value }, errores: [], valida: false } : row) })) }
  function updateOption(rowIndex, optionIndex, value) { setPreview((current) => ({ ...current, filas: current.filas.map((row, i) => i === rowIndex ? { ...row, datos: { ...row.datos, opciones: row.datos.opciones.map((option, j) => j === optionIndex ? { ...option, texto: value } : option) }, errores: [], valida: false } : row) })) }
  function removeRow(index) { setPreview((current) => ({ ...current, filas: current.filas.filter((_, i) => i !== index), validas: 0, invalidas: 0 })) }
  return <section className="management-section"><div className="section-heading"><div><p className="eyebrow">Carga masiva</p><h2>Importar preguntas</h2></div><button className="secondary-button" onClick={async () => { const blob = await api.descargarPlantilla(); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'plantilla_preguntas.xlsx'; a.click(); URL.revokeObjectURL(url) }}>Descargar plantilla</button></div><div className="upload-box"><label htmlFor="import-quiz">Cuestionario destino (opcional)</label><select id="import-quiz" value={quizId} onChange={(event) => setQuizId(event.target.value)} disabled={loading}><option value="">Solo agregar al banco</option>{quizzes.map((quiz) => <option key={quiz.id} value={quiz.id}>{quiz.nombre}</option>)}</select><label htmlFor="excel-file">Selecciona un archivo Excel</label><input id="excel-file" type="file" accept=".xlsx,.xls" onChange={previewFile} disabled={loading} /><p>La vista previa permite corregir, eliminar y validar cada fila antes de guardarla. Si eliges un borrador, se asignarán al cuestionario al confirmar.</p></div>{notice && <p className="form-message form-message--success" role="status">{notice}</p>}{error && <p className="form-message form-message--error">{error}</p>}{preview && <div className="import-preview"><h3>Revisión antes de guardar</h3><p>{preview.validas ?? 0} filas válidas · {preview.invalidas ?? 0} con errores</p><div className="import-rows">{preview.filas.map((row, index) => <article className={row.valida ? 'import-row import-row--valid' : 'import-row import-row--error'} key={`${row.numero}-${index}`}><div className="import-row__header"><strong>Fila {row.numero}</strong><span>{row.valida ? 'Lista para guardar' : 'Requiere corrección'}</span><button className="text-button" type="button" onClick={() => removeRow(index)}>Eliminar</button></div>{row.errores.length > 0 && <ul className="import-errors">{row.errores.map((item) => <li key={item}>{item}</li>)}</ul>}<div className="import-row__fields"><label>Categoría<select value={row.datos.categoria || ''} onChange={(e) => updateRow(index, 'categoria', e.target.value)}><option value="">Selecciona</option>{categories.map((category) => <option key={category.id} value={category.nombre}>{category.nombre}</option>)}</select></label><label>Competencia<select value={row.datos.competencia || ''} onChange={(e) => updateRow(index, 'competencia', e.target.value)}><option value="">Selecciona</option>{competencies.map((competency) => <option key={competency.id} value={competency.nombre}>{competency.nombre}</option>)}</select></label><label className="import-field--wide">Enunciado<textarea value={row.datos.enunciado || ''} onChange={(e) => updateRow(index, 'enunciado', e.target.value)} /></label>{row.datos.opciones.map((option, optionIndex) => <label key={option.letra}>Opción {option.letra}<input value={option.texto || ''} onChange={(e) => updateOption(index, optionIndex, e.target.value)} /></label>)}<label>Correcta<input value={(row.datos.correctas || []).join(', ')} onChange={(e) => updateRow(index, 'correctas', e.target.value.split(',').map((x) => x.trim().toUpperCase()).filter(Boolean))} /></label></div></article>)}</div><div className="dialog-actions"><button className="secondary-button" type="button" onClick={revalidate} disabled={loading}>Volver a validar</button>{preview.validas === preview.total && preview.total > 0 && <button className="primary-button" type="button" onClick={confirm}>Confirmar importación</button>}</div></div>}{!preview && <div className="data-list">{items.map((item) => <article className="data-row" key={item.id}><div><h3>{item.archivo_nombre}</h3><p>{item.total} filas · {item.preguntas_creadas} preguntas creadas</p></div><span className="status">{item.estado}</span></article>)}</div>}</section>
}

function LoadingScreen({ text }) { return <main className="app-shell"><section className="content-column state-page"><div className="state-block" role="status"><span className="loading-dot" aria-hidden="true" /><p>{text}</p></div></section></main> }
function ErrorScreen({ error, onBack }) { return <main className="app-shell"><section className="content-column state-page"><div className="state-block state-block--error" role="alert"><p>{error}</p><button className="secondary-button" onClick={onBack}>Volver</button></div></section></main> }

export default App
