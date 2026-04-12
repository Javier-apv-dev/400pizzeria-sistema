import { useState, useEffect } from 'react'
import { Plus, Ban, Trash2 } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import pagosService from '../../services/pagosService'
import pedidosService from '../../services/pedidosService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Pagos.module.css'

const ESTADOS_FILTRO = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendientes' },
  { value: 'completado', label: 'Completados' },
  { value: 'anulado', label: 'Anulados' },
]

const METODOS_PAGO = [
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'debito', label: 'Débito' },
  { value: 'credito', label: 'Crédito' },
  { value: 'transferencia', label: 'Transferencia' },
]

function Pagos() {
  const { user } = useAuth()
  const rolUsuario = user?.rol?.nombre

  const [pagos, setPagos] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState('')

  // Modal
  const [modalOpen, setModalOpen] = useState(false)
  const [pedidosSinPago, setPedidosSinPago] = useState([])
  const [selectedPedido, setSelectedPedido] = useState(null)
  const [metodoPago, setMetodoPago] = useState('efectivo')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  useEffect(() => {
    loadPagos()
  }, [filtro])

  async function loadPagos() {
    try {
      const response = filtro
        ? await pagosService.getByEstado(filtro)
        : await pagosService.getAll()
      setPagos(response.data)
    } catch (error) {
      toast.error('Error al cargar los pagos')
    } finally {
      setLoading(false)
    }
  }

  async function handleOpenModal() {
    setFormError('')
    setMetodoPago('efectivo')
    setSelectedPedido(null)

    try {
      const response = await pedidosService.getByEstado('entregado')
      const pedidosEntregados = response.data

      const pagosResponse = await pagosService.getAll()
      const pedidosConPago = pagosResponse.data
        .filter(p => p.estado !== 'anulado')
        .map(p => p.pedido?.id || p.pedido_id)

      const disponibles = pedidosEntregados.filter(p => !pedidosConPago.includes(p.id))
      setPedidosSinPago(disponibles)

      if (disponibles.length === 0) {
        toast.error('No hay pedidos entregados pendientes de pago')
        return
      }

      setSelectedPedido(disponibles[0])
      setModalOpen(true)
    } catch (error) {
      toast.error('Error al cargar pedidos disponibles')
    }
  }

  async function handleSave(e) {
    e.preventDefault()
    if (!selectedPedido) return
    setFormError('')
    setSaving(true)

    try {
      await pagosService.create({
        pedido_id: selectedPedido.id,
        metodo_pago: metodoPago,
        monto: selectedPedido.total,
      })
      toast.success('Pago registrado')
      setModalOpen(false)
      loadPagos()
    } catch (error) {
      const msg = error.response?.data?.detail || error.response?.data?.pedido_id?.[0] || 'Error al registrar el pago'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleAnular(pago) {
    if (!window.confirm(`¿Anular el pago #${pago.id}?`)) return

    try {
      await pagosService.anular(pago.id)
      toast.success('Pago anulado')
      loadPagos()
    } catch (error) {
      toast.error('Error al anular el pago')
    }
  }

  async function handleDelete(pago) {
    if (!window.confirm(`¿Eliminar permanentemente el pago #${pago.id}?`)) return

    try {
      await pagosService.delete(pago.id)
      toast.success('Pago eliminado')
      loadPagos()
    } catch (error) {
      toast.error('Error al eliminar el pago')
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
      completado: styles.badgeCompletado,
      anulado: styles.badgeAnulado,
    }
    const labels = {
      pendiente: 'Pendiente',
      completado: 'Completado',
      anulado: 'Anulado',
    }
    return (
      <span className={`${styles.badge} ${clases[estado] || ''}`}>
        {labels[estado] || estado}
      </span>
    )
  }

  function getMetodoLabel(metodo) {
    const found = METODOS_PAGO.find(m => m.value === metodo)
    return found ? found.label : metodo
  }

  function getUsuarioName(usuario) {
    if (!usuario) return '—'
    return `${usuario.nombre} ${usuario.apellido}`
  }

  return (
    <div>
      <Toaster position="top-right" />

      <div className={styles.header}>
        <h1 className={styles.title}>Pagos</h1>
        <div className={styles.headerActions}>
          <div className={styles.filters}>
            {ESTADOS_FILTRO.map((estado) => (
              <button
                key={estado.value}
                className={`${styles.filterButton} ${filtro === estado.value ? styles.filterButtonActive : ''}`}
                onClick={() => setFiltro(estado.value)}
              >
                {estado.label}
              </button>
            ))}
          </div>
          <button className={styles.addButton} onClick={handleOpenModal}>
            <Plus size={18} />
            Registrar pago
          </button>
        </div>
      </div>

      {loading ? (
        <div className={styles.loading}>Cargando pagos...</div>
      ) : pagos.length === 0 ? (
        <div className={styles.empty}>No hay pagos registrados</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Pedido</th>
              <th>Mesa</th>
              <th>Método</th>
              <th>Monto</th>
              <th>Estado</th>
              <th>Registrado por</th>
              <th>Fecha</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {pagos.map((pago) => (
              <tr key={pago.id}>
                <td>{pago.id}</td>
                <td>#{pago.pedido?.id || pago.pedido_id}</td>
                <td>Mesa {pago.pedido?.mesa?.numero || pago.pedido?.mesa_id || '—'}</td>
                <td>
                  <span className={`${styles.badge} ${styles.metodoBadge}`}>
                    {getMetodoLabel(pago.metodo_pago)}
                  </span>
                </td>
                <td>
                  <span className={styles.monto}>{formatPrice(pago.monto)}</span>
                </td>
                <td>{getEstadoBadge(pago.estado)}</td>
                <td>
                  {pago.estado === 'anulado'
                    ? <span className={styles.anulado}>Anulado por {getUsuarioName(pago.anulado_por)}</span>
                    : getUsuarioName(pago.registrado_por)
                  }
                </td>
                <td>{formatDate(pago.fecha)}</td>
                <td>
                  <div className={styles.actions}>
                    {pago.estado === 'completado' && (
                      <button className={styles.anularButton} onClick={() => handleAnular(pago)}>
                        <Ban size={14} /> Anular
                      </button>
                    )}
                    {pago.estado === 'anulado' && rolUsuario === 'Administrador' && (
                      <button className={styles.deleteBtn} onClick={() => handleDelete(pago)}>
                        <Trash2 size={14} /> Eliminar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Modal registrar pago */}
      {modalOpen && (
        <div className={styles.modalOverlay} onClick={() => setModalOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>Registrar pago</h2>

            <form className={styles.form} onSubmit={handleSave}>
              {formError && <div className={styles.error}>{formError}</div>}

              <div className={styles.inputGroup}>
                <label className={styles.label}>Pedido</label>
                <select
                  className={styles.select}
                  value={selectedPedido?.id || ''}
                  onChange={(e) => {
                    const pedido = pedidosSinPago.find(p => p.id === Number(e.target.value))
                    setSelectedPedido(pedido)
                  }}
                >
                  {pedidosSinPago.map((pedido) => (
                    <option key={pedido.id} value={pedido.id}>
                      Pedido #{pedido.id} — Mesa {pedido.mesa?.numero || pedido.mesa_id}
                    </option>
                  ))}
                </select>
              </div>

              {selectedPedido && (
                <div className={styles.pedidoInfo}>
                  <div className={styles.pedidoInfoRow}>
                    <span className={styles.pedidoInfoLabel}>Mesa</span>
                    <span className={styles.pedidoInfoValue}>
                      Mesa {selectedPedido.mesa?.numero || selectedPedido.mesa_id}
                    </span>
                  </div>
                  {selectedPedido.detalles?.map((det, i) => (
                    <div key={i} className={styles.pedidoInfoRow}>
                      <span className={styles.pedidoInfoLabel}>
                        {det.producto?.nombre || `Producto ${det.producto_id}`} x{det.cantidad}
                      </span>
                      <span className={styles.pedidoInfoValue}>{formatPrice(det.subtotal)}</span>
                    </div>
                  ))}
                  <div className={styles.pedidoInfoRow} style={{ marginTop: '0.5rem', borderTop: '1px solid var(--color-bg-hover)', paddingTop: '0.5rem' }}>
                    <span className={styles.pedidoInfoLabel}>Total a cobrar</span>
                    <span className={styles.pedidoInfoTotal}>{formatPrice(selectedPedido.total)}</span>
                  </div>
                </div>
              )}

              <div className={styles.inputGroup}>
                <label className={styles.label}>Método de pago</label>
                <select
                  className={styles.select}
                  value={metodoPago}
                  onChange={(e) => setMetodoPago(e.target.value)}
                >
                  {METODOS_PAGO.map((metodo) => (
                    <option key={metodo.value} value={metodo.value}>{metodo.label}</option>
                  ))}
                </select>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelButton} onClick={() => setModalOpen(false)}>
                  Cancelar
                </button>
                <button type="submit" className={styles.saveButton} disabled={saving}>
                  {saving ? 'Registrando...' : 'Registrar pago'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Pagos