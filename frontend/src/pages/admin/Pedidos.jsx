import { useAuth } from '../../context/AuthContext'
import { useState, useEffect } from 'react'
import { Trash2, ChefHat, UtensilsCrossed, CheckCircle, ArrowRight } from 'lucide-react'
import pedidosService from '../../services/pedidosService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Pedidos.module.css'

const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendientes' },
  { value: 'en_preparacion', label: 'En preparación' },
  { value: 'listo', label: 'Listos' },
  { value: 'entregado', label: 'Entregados' },
]

const NEXT_ESTADO = {
  pendiente: { value: 'en_preparacion', label: 'Preparar', icon: ChefHat },
  en_preparacion: { value: 'listo', label: 'Marcar listo', icon: UtensilsCrossed },
  listo: { value: 'entregado', label: 'Entregar', icon: CheckCircle },
}

function Pedidos() {
  const { user } = useAuth()
  const rolUsuario = user?.rol?.nombre

  const [pedidos, setPedidos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('')

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
      toast.error('Error al actualizar el estado')
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
        <div className={styles.empty}>No hay pedidos {filtro && `con estado "${filtro}"`}</div>
      ) : (
        <div className={styles.grid}>
          {pedidos.map((pedido) => (
            <div key={pedido.id} className={styles.card}>
              {/* Header */}
              <div className={styles.cardHeader}>
                <div>
                  <span className={styles.pedidoId}>Pedido #{pedido.id}</span>
                  <div className={styles.fecha}>{formatDate(pedido.fecha_creacion)}</div>
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
              </div>

              {/* Footer con acciones */}
              <div className={styles.cardFooter}>
                {/* Garzón: puede enviar a cocina (pendiente → en_preparacion) */}
                {pedido.estado === 'pendiente' && (rolUsuario === 'Garzon' || rolUsuario === 'Administrador') && (
                  <button
                    className={`${styles.estadoButton} ${styles.nextButton}`}
                    onClick={() => handleNextEstado(pedido)}
                  >
                    <ArrowRight size={16} />
                    Preparar
                  </button>
                )}

                {/* Cocina: puede marcar como listo (en_preparacion → listo) */}
                {pedido.estado === 'en_preparacion' && (rolUsuario === 'Cocina' || rolUsuario === 'Administrador') && (
                  <button
                    className={`${styles.estadoButton} ${styles.nextButton}`}
                    onClick={() => handleNextEstado(pedido)}
                  >
                    <ArrowRight size={16} />
                    Marcar listo
                  </button>
                )}

                {/* Garzón: puede marcar como entregado (listo → entregado) */}
                {pedido.estado === 'listo' && (rolUsuario === 'Garzon' || rolUsuario === 'Administrador') && (
                  <button
                    className={`${styles.estadoButton} ${styles.nextButton}`}
                    onClick={() => handleNextEstado(pedido)}
                  >
                    <ArrowRight size={16} />
                    Entregar
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