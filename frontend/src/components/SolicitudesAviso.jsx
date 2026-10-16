import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { BellRing, Receipt, Check } from 'lucide-react'
import solicitudesService from '../services/solicitudesService'
import { sonarAviso } from '../utils/avisoSonoro'
import styles from './SolicitudesAviso.module.css'

// Mismo intervalo que la pantalla de pedidos
const INTERVALO_MS = 10000

function hace(fecha) {
  const minutos = Math.floor((Date.now() - new Date(fecha)) / 60000)
  return minutos < 1 ? 'recién' : `hace ${minutos} min`
}

// Avisos pendientes de las mesas (llamar al garzón, pedir la cuenta).
// Se muestra arriba de cualquier pantalla del panel para Garzón y Administrador.
function SolicitudesAviso() {
  const [solicitudes, setSolicitudes] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let montado = true
    // Solicitudes ya vistas; null hasta la primera carga (que no suena)
    let idsVistos = null
    function cargar() {
      solicitudesService.getPendientes()
        .then(response => {
          if (!montado) return
          if (idsVistos && response.data.some(s => !idsVistos.has(s.id))) {
            sonarAviso()
          }
          idsVistos = new Set(response.data.map(s => s.id))
          setSolicitudes(response.data)
        })
        // Si falla una consulta se mantiene la lista anterior; la siguiente lo reintenta
        .catch(() => {})
    }
    cargar()
    const interval = setInterval(cargar, INTERVALO_MS)
    return () => {
      montado = false
      clearInterval(interval)
    }
  }, [])

  async function atender(solicitud) {
    setError('')
    try {
      await solicitudesService.atender(solicitud.id)
      setSolicitudes(prev => prev.filter(s => s.id !== solicitud.id))
    } catch (err) {
      // La siguiente consulta (máx. 10 s) deja la lista al día
      setError(err.response?.data?.error || 'No se pudo marcar como atendida')
    }
  }

  if (solicitudes.length === 0) return null

  return (
    <section className={styles.aviso} aria-live="polite">
      {solicitudes.map(solicitud => {
        const Icono = solicitud.tipo === 'cuenta' ? Receipt : BellRing
        return (
          <div key={solicitud.id} className={styles.item}>
            <Icono size={18} className={styles.icono} />
            <span className={styles.texto}>
              <strong>Mesa {solicitud.mesa_numero}</strong> · {solicitud.tipo_display}
              <span className={styles.tiempo}> · {hace(solicitud.creada_en)}</span>
            </span>
            {solicitud.tipo === 'cuenta' && (
              <Link to="/admin/pagos" className={styles.link}>Cobrar</Link>
            )}
            <button className={styles.atender} onClick={() => atender(solicitud)}>
              <Check size={14} />
              Atender
            </button>
          </div>
        )
      })}
      {error && <p className={styles.error}>{error}</p>}
    </section>
  )
}

export default SolicitudesAviso
