import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Outlet } from 'react-router-dom'
import { BellRing, Receipt } from 'lucide-react'
import { CartProvider } from '../context/CartContext'
import mesasService from '../services/mesasService'
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
  // El QR trae el id interno de la mesa; al cliente se le muestra su número
  const mesa = searchParams.get('mesa')
  const [mesaNumero, setMesaNumero] = useState(null)
  const [mesaInexistente, setMesaInexistente] = useState(false)
  // Estado de cada botón: undefined | 'enviando' | 'avisado' | 'error'
  const [avisos, setAvisos] = useState({})

  useEffect(() => {
    if (!mesa) return
    let montado = true
    mesasService.getById(mesa)
      .then(response => { if (montado) setMesaNumero(response.data.numero) })
      .catch(error => { if (montado && error.response?.status === 404) setMesaInexistente(true) })
    return () => { montado = false }
  }, [mesa])

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
        {mesa && !mesaInexistente && (
          <p className={styles.mesaInfo}>{mesaNumero ? `Mesa ${mesaNumero}` : ' '}</p>
        )}
        {mesaInexistente && (
          <p className={styles.mesaError}>
            No encontramos esta mesa. Escanea de nuevo el código QR o pide ayuda al personal.
          </p>
        )}

        {mesa && !mesaInexistente && (
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
        {/* key: al cambiar de mesa se carga el carrito guardado de esa mesa */}
        <CartProvider key={mesa} mesa={mesa}>
          <Outlet />
        </CartProvider>
      </main>
    </div>
  )
}

export default CartaLayout
