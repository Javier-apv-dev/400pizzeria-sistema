import { useAuth } from '../../context/AuthContext'
import { useState, useEffect } from 'react'
import { Trash2, ChefHat, UtensilsCrossed, CheckCircle, ArrowRight } from 'lucide-react'
import pedidosService from '../../services/pedidosService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Pedidos.module.css'

const ESTADOS = [
  { value: 'activos', label: 'Activos' },
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendientes' },
  { value: 'en_preparacion', label: 'En preparación' },
  { value: 'listo', label: 'Listos' },
  { value: 'entregado', label: 'Entregados' },
]

const ETIQUETAS_ESTADO = {
  pendiente: 'Recibido',
  en_preparacion: 'En preparación',
  listo: 'Listo',
  entregado: 'Entregado',
}

// Mismas reglas que TRANSICIONES en el backend (apps/pedidos/views.py)
const NEXT_ESTADO = {
  pendiente: { value: 'en_preparacion', label: 'Preparar', icon: ChefHat, roles: ['Administrador', 'Garzon', 'Cocina'] },
  en_preparacion: { value: 'listo', label: 'Marcar listo', icon: UtensilsCrossed, roles: ['Administrador', 'Cocina'] },
  listo: { value: 'entregado', label: 'Entregar', icon: CheckCircle, roles: ['Administrador', 'Garzon'] },
}

// Minutos en el estado actual a partir de los cuales el pedido se destaca
const MINUTOS_ALERTA = 15
const MINUTOS_CRITICO = 25

function minutosEnEstado(pedido) {
  const ultimo = pedido.historial?.[pedido.historial.length - 1]
  const desde = new Date(ultimo?.fecha || pedido.fecha_creacion)
  return Math.max(0, Math.floor((Date.now() - desde) / 60000))
}

function formatMinutos(minutos) {
  if (minutos < 1) return 'recién'
  if (minutos < 60) return `hace ${minutos} min`
  return `hace ${Math.floor(minutos / 60)} h ${minutos % 60} min`
}

function formatHora(fecha) {
  return new Date(fecha).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
}

function Pedidos() {
  const { user } = useAuth()
  const rolUsuario = user?.rol?.nombre

  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('activos')

  useEffect(() => {
    loadPedidos()

    // Auto-refrescar cada 10 segundos
    const interval = setInterval(() => {
      loadPedidos()
    }, 10000)

    return () => clearInterval(interval)
  }, [filtro])

  async function loadPedidos() {
    try {
      if (filtro === 'activos') {
        // Lo que falta por atender, del más antiguo al más nuevo (orden de cocina)
        const response = await pedidosService.getAll()
        setPedidos(
          response.data
            .filter(p => p.estado !== 'entregado')
            .sort((a, b) => new Date(a.fecha_creacion) - new Date(b.fecha_creacion))
        )
        return
      }
      const response = filtro
        ? await pedidosService.getByEstado(filtro)
        : await pedidosService.getAll()
      setPedidos(response.data)
    } catch (error) {
      toast.error('Error al cargar los pedidos')
    } finally {
      setLoading(false)
    }
  }

  async function handleNextEstado(pedido) {
    const next = NEXT_ESTADO[pedido.estado]
    if (!next) return

    try {
      await pedidosService.updateEstado(pedido.id, next.value)
      toast.success(`Pedido #${pedido.id} → ${next.label}`)
      loadPedidos()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al actualizar el estado')
    }
  }

  async function handleDelete(pedido) {
    if (pedido.estado !== 'pendiente') {
      toast.error('Solo se pueden eliminar pedidos pendientes')
      return
    }
    if (!window.confirm(`¿Eliminar el pedido #${pedido.id}?`)) return

    try {
      await pedidosService.delete(pedido.id)
      toast.success('Pedido eliminado')
      loadPedidos()
    } catch (error) {
      toast.error('Error al eliminar el pedido')
    }
  }

  function formatPrice(price) {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleString('es-CL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  function getEstadoBadge(estado) {
    const clases = {
      pendiente: styles.badgePendiente,
      en_preparacion: styles.badgeEnPreparacion,
      listo: styles.badgeListo,
      entregado: styles.badgeEntregado,
    }
    const labels = {
      pendiente: 'Pendiente',
      en_preparacion: 'En preparación',
      listo: 'Listo',
      entregado: 'Entregado',
    }
    return (
      <span className={`${styles.badge} ${clases[estado] || ''}`}>
        {labels[estado] || estado}
      </span>
    )
  }

  // Cuánto lleva el pedido en su estado actual; ámbar o rojo si se está demorando
  function getTiempoEnEstado(pedido) {
    if (pedido.estado === 'entregado') return null
    const minutos = minutosEnEstado(pedido)
    const nivel = minutos >= MINUTOS_CRITICO
      ? styles.tiempoCritico
      : minutos >= MINUTOS_ALERTA ? styles.tiempoAlerta : ''
    return (
      <div className={`${styles.tiempo} ${nivel}`}>
        {ETIQUETAS_ESTADO[pedido.estado]} {formatMinutos(minutos)}
      </div>
    )
  }

  function getMesaLabel(pedido) {
    if (pedido.mesa?.numero) return `Mesa ${pedido.mesa.numero}`
    if (pedido.mesa_id) return `Mesa ${pedido.mesa_id}`
    return 'Sin mesa'
  }

  return (
    <div>
      <Toaster position="top-right" />

      <div className={styles.header}>
        <h1 className={styles.title}>Pedidos</h1>
        <div className={styles.filters}>
          {ESTADOS.map((estado) => (
            <button
              key={estado.value}
              className={`${styles.filterButton} ${filtro === estado.value ? styles.filterButtonActive : ''}`}
              onClick={() => setFiltro(estado.value)}
            >
              {estado.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className={styles.loading}>Cargando pedidos...</div>
      ) : pedidos.length === 0 ? (
        <div className={styles.empty}>
          {filtro === 'activos'
            ? 'No hay pedidos activos'
            : `No hay pedidos${filtro ? ` con estado "${filtro}"` : ''}`}
        </div>
      ) : (
        <div className={styles.grid}>
          {pedidos.map((pedido) => (
            <div key={pedido.id} className={styles.card}>
              {/* Header */}
              <div className={styles.cardHeader}>
                <div>
                  <span className={styles.pedidoId}>Pedido #{pedido.id}</span>
                  <div className={styles.fecha}>{formatDate(pedido.fecha_creacion)}</div>
                  {getTiempoEnEstado(pedido)}
                </div>
                {getEstadoBadge(pedido.estado)}
              </div>

              {/* Body */}
              <div className={styles.cardBody}>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Mesa</span>
                  <span className={styles.infoValue}>{getMesaLabel(pedido)}</span>
                </div>

                {/* Detalle de productos */}
                {pedido.detalles && pedido.detalles.length > 0 && (
                  <div className={styles.detailSection}>
                    <div className={styles.detailTitle}>Productos</div>
                    {pedido.detalles.map((detalle, index) => (
                      <div key={index} className={styles.detailItem}>
                        <div>
                          <span className={styles.detailProduct}>
                            {detalle.producto?.nombre || `Producto ${detalle.producto_id}`}
                          </span>
                          <span className={styles.detailQuantity}>x{detalle.cantidad}</span>
                          {detalle.nota && (
                            <div className={styles.detailNota}>{detalle.nota}</div>
                          )}
                        </div>
                        <span className={styles.detailSubtotal}>
                          {formatPrice(detalle.subtotal)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Total */}
                <div className={styles.totalRow}>
                  <span className={styles.totalLabel}>Total</span>
                  <span className={styles.totalValue}>{formatPrice(pedido.total)}</span>
                </div>

                {/* Seguimiento: hora de cada etapa (el nombre de quien la hizo, al pasar el mouse) */}
                {pedido.historial?.length > 0 && (
                  <div className={styles.seguimiento}>
                    {pedido.historial.map((paso, index) => (
                      <span
                        key={index}
                        className={styles.seguimientoPaso}
                        title={paso.usuario || 'Cliente, desde la carta'}
                      >
                        {ETIQUETAS_ESTADO[paso.estado]} {formatHora(paso.fecha)}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer con acciones */}
              <div className={styles.cardFooter}>
                {/* Avance al siguiente estado, solo para los roles que pueden hacerlo */}
                {NEXT_ESTADO[pedido.estado]?.roles.includes(rolUsuario) && (
                  <button
                    className={`${styles.estadoButton} ${styles.nextButton}`}
                    onClick={() => handleNextEstado(pedido)}
                  >
                    <ArrowRight size={16} />
                    {NEXT_ESTADO[pedido.estado].label}
                  </button>
                )}

                {/* Solo admin puede eliminar pedidos pendientes */}
                {pedido.estado === 'pendiente' && rolUsuario === 'Administrador' && (
                  <button
                    className={styles.deleteButton}
                    onClick={() => handleDelete(pedido)}
                  >
                    <Trash2 size={18} />
                  </button>
                )}

                {pedido.estado === 'entregado' && (
                  <span className={styles.fecha}>Pedido completado</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Pedidos