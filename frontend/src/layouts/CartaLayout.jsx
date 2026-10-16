import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Outlet } from 'react-router-dom'
import { BellRing, Receipt } from 'lucide-react'
import solicitudesService from '../services/solicitudesService'
import styles from './CartaLayout.module.css'

// Tiempo que el botón queda en "Avisado" antes de permitir otro aviso
const ESPERA_MS = 60000

const ACCIONES = [
  { tipo: 'garzon', label: 'Llamar al garzón', icon: BellRing },
  { tipo: 'cuenta', label: 'Pedir la cuenta', icon: Receipt },
]

function CartaLayout() {
  const [searchParams] = useSearchParams()
  const mesa = searchParams.get('mesa')
  // Estado de cada botón: undefined | 'enviando' | 'avisado' | 'error'
  const [avisos, setAvisos] = useState({})

  async function solicitar(tipo) {
    setAvisos(prev => ({ ...prev, [tipo]: 'enviando' }))
    try {
      await solicitudesService.crear(mesa, tipo)
      setAvisos(prev => ({ ...prev, [tipo]: 'avisado' }))
      setTimeout(() => setAvisos(prev => ({ ...prev, [tipo]: undefined })), ESPERA_MS)
    } catch {
      setAvisos(prev => ({ ...prev, [tipo]: 'error' }))
    }
  }

  function textoBoton(accion) {
    const estado = avisos[accion.tipo]
    if (estado === 'enviando') return 'Avisando...'
    if (estado === 'avisado') return 'Avisado, ya viene'
    if (estado === 'error') return 'No se pudo avisar, reintenta'
    return accion.label
  }

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <img
          src="https://tofuu.getjusto.com/orioneat-local/resized2/Kra3Qq86eTHF5EhfY-300-x.webp"
          alt="400 Pizzería"
          className={styles.logo}
        />
        <h1 className={styles.title}>400 Pizzería</h1>
        {mesa && <p className={styles.mesaInfo}>Mesa {mesa}</p>}

        {mesa && (
          <div className={styles.acciones}>
            {ACCIONES.map(accion => {
              const estado = avisos[accion.tipo]
              return (
                <button
                  key={accion.tipo}
                  className={`${styles.accionButton} ${estado === 'avisado' ? styles.accionAvisada : ''} ${estado === 'error' ? styles.accionError : ''}`}
                  onClick={() => solicitar(accion.tipo)}
                  disabled={estado === 'enviando' || estado === 'avisado'}
                >
                  <accion.icon size={16} />
                  {textoBoton(accion)}
                </button>
              )
            })}
          </div>
        )}
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}

export default CartaLayout
