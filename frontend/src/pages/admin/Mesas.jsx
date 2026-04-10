import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, RefreshCw, Download } from 'lucide-react'
import mesasService from '../../services/mesasService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Mesas.module.css'

function Mesas() {
  const [mesas, setMesas] = useState([])
  const [loading, setLoading] = useState(true)

  // Modal
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState({ numero: '', capacidad: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  useEffect(() => {
    loadMesas()
  }, [])

  async function loadMesas() {
    try {
      const response = await mesasService.getAll()
      setMesas(response.data)
    } catch (error) {
      toast.error('Error al cargar las mesas')
    } finally {
      setLoading(false)
    }
  }

  function handleCreate() {
    setEditing(null)
    setFormData({ numero: '', capacidad: '' })
    setFormError('')
    setModalOpen(true)
  }

  function handleEdit(mesa) {
    setEditing(mesa)
    setFormData({ numero: mesa.numero, capacidad: mesa.capacidad })
    setFormError('')
    setModalOpen(true)
  }

  async function handleSave(e) {
    e.preventDefault()
    setFormError('')
    setSaving(true)

    try {
      if (editing) {
        await mesasService.update(editing.id, formData)
        toast.success('Mesa actualizada')
      } else {
        await mesasService.create(formData)
        toast.success('Mesa creada con código QR')
      }
      setModalOpen(false)
      loadMesas()
    } catch (error) {
      const msg = error.response?.data?.numero?.[0] || error.response?.data?.detail || 'Error al guardar'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(mesa) {
    if (!window.confirm(`¿Eliminar la mesa ${mesa.numero}?`)) return

    try {
      await mesasService.delete(mesa.id)
      toast.success('Mesa eliminada')
      loadMesas()
    } catch (error) {
      toast.error('Error al eliminar la mesa')
    }
  }

  async function handleEstadoChange(mesa, nuevoEstado) {
    try {
      await mesasService.updateEstado(mesa.id, nuevoEstado)
      toast.success(`Mesa ${mesa.numero} → ${nuevoEstado}`)
      loadMesas()
    } catch (error) {
      toast.error('Error al cambiar el estado')
    }
  }

  async function handleRegenerarQR(mesa) {
    try {
      await mesasService.regenerarQR(mesa.id)
      toast.success(`QR regenerado para mesa ${mesa.numero}`)
      loadMesas()
    } catch (error) {
      toast.error('Error al regenerar el QR')
    }
  }

  function handleDescargarQR(mesa) {
    if (!mesa.qr_code) return

    const link = document.createElement('a')
    link.href = mesa.qr_code.startsWith('data:')
      ? mesa.qr_code
      : `data:image/png;base64,${mesa.qr_code}`
    link.download = `mesa_${mesa.numero}_qr.png`
    link.click()
  }

  function getEstadoBadge(estado) {
    const clases = {
      libre: styles.badgeLibre,
      ocupada: styles.badgeOcupada,
      reservada: styles.badgeReservada,
    }
    return `${styles.badge} ${clases[estado] || ''}`
  }

  function getQRSrc(mesa) {
    if (!mesa.qr_code) return null
    return mesa.qr_code.startsWith('data:')
      ? mesa.qr_code
      : `data:image/png;base64,${mesa.qr_code}`
  }

  return (
    <div>
      <Toaster position="top-right" />

      <div className={styles.header}>
        <h1 className={styles.title}>Mesas</h1>
        <button className={styles.addButton} onClick={handleCreate}>
          <Plus size={18} />
          Nueva mesa
        </button>
      </div>

      {loading ? (
        <div className={styles.loading}>Cargando mesas...</div>
      ) : mesas.length === 0 ? (
        <div className={styles.empty}>No hay mesas registradas</div>
      ) : (
        <div className={styles.grid}>
          {mesas.map((mesa) => (
            <div key={mesa.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <span className={styles.mesaNumber}>Mesa {mesa.numero}</span>
                <div className={styles.cardActions}>
                  <button className={styles.editButton} onClick={() => handleEdit(mesa)}>
                    <Pencil size={16} />
                  </button>
                  <button className={styles.deleteButton} onClick={() => handleDelete(mesa)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              <div className={styles.cardInfo}>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Capacidad</span>
                  <span className={styles.infoValue}>{mesa.capacidad} personas</span>
                </div>
                <div className={styles.infoRow}>
                  <span className={styles.infoLabel}>Estado</span>
                  <select
                    className={styles.estadoSelect}
                    value={mesa.estado}
                    onChange={(e) => handleEstadoChange(mesa, e.target.value)}
                  >
                    <option value="libre">Libre</option>
                    <option value="ocupada">Ocupada</option>
                    <option value="reservada">Reservada</option>
                  </select>
                </div>
              </div>

              <div className={styles.qrContainer}>
                {getQRSrc(mesa) ? (
                  <img
                    src={getQRSrc(mesa)}
                    alt={`QR Mesa ${mesa.numero}`}
                    className={styles.qrImage}
                  />
                ) : (
                  <div className={styles.empty}>Sin QR</div>
                )}
                <div className={styles.qrActions}>
                  <button className={styles.qrButton} onClick={() => handleRegenerarQR(mesa)}>
                    <RefreshCw size={14} />
                    Regenerar
                  </button>
                  <button className={styles.qrButton} onClick={() => handleDescargarQR(mesa)}>
                    <Download size={14} />
                    Descargar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal crear/editar */}
      {modalOpen && (
        <div className={styles.modalOverlay} onClick={() => setModalOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>
              {editing ? 'Editar mesa' : 'Nueva mesa'}
            </h2>

            <form className={styles.form} onSubmit={handleSave}>
              {formError && <div className={styles.error}>{formError}</div>}

              <div className={styles.row}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Número de mesa</label>
                  <input
                    type="number"
                    className={styles.input}
                    placeholder="Ej: 1"
                    value={formData.numero}
                    onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
                    min="1"
                    required
                  />
                </div>

                <div className={styles.inputGroup}>
                  <label className={styles.label}>Capacidad</label>
                  <input
                    type="number"
                    className={styles.input}
                    placeholder="Ej: 4"
                    value={formData.capacidad}
                    onChange={(e) => setFormData({ ...formData, capacidad: e.target.value })}
                    min="1"
                    required
                  />
                </div>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelButton} onClick={() => setModalOpen(false)}>
                  Cancelar
                </button>
                <button type="submit" className={styles.saveButton} disabled={saving}>
                  {saving ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Mesas