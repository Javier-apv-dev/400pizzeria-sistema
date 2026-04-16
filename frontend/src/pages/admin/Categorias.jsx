import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import categoriasService from '../../services/categoriasService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Categorias.module.css'

function Categorias() {
  // Estado del listado
  const [categorias, setCategorias] = useState([])
  const [loading, setLoading] = useState(true)

  // Estado del modal
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState({ nombre: '', descripcion: '', activo: true })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // Cargar categorías al montar el componente
  useEffect(() => {
    loadCategorias()
  }, [])

  async function loadCategorias() {
    try {
      const response = await categoriasService.getAll()
      setCategorias(response.data)
    } catch (error) {
      toast.error('Error al cargar las categorías')
    } finally {
      setLoading(false)
    }
  }

  // Abrir modal para crear
  function handleCreate() {
    setEditing(null)
    setFormData({ nombre: '', descripcion: '', activo: true })
    setFormError('')
    setModalOpen(true)
  }

  // Abrir modal para editar
  function handleEdit(categoria) {
    setEditing(categoria)
    setFormData({
      nombre: categoria.nombre,
      descripcion: categoria.descripcion || '',
      activo: categoria.activo,
    })
    setFormError('')
    setModalOpen(true)
  }

  // Guardar (crear o editar)
  async function handleSave(e) {
    e.preventDefault()
    setFormError('')
    setSaving(true)

    try {
      if (editing) {
        await categoriasService.update(editing.id, formData)
        toast.success('Categoría actualizada')
      } else {
        await categoriasService.create(formData)
        toast.success('Categoría creada')
      }
      setModalOpen(false)
      loadCategorias()
    } catch (error) {
      const msg = error.response?.data?.nombre?.[0] || 'Error al guardar'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  // Desactivar (desactivar)
  async function handleToggleEstado(categoria) {
  const nuevoEstado = !categoria.activo
  const accion = nuevoEstado ? 'activar' : 'desactivar'
  if (!window.confirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} la categoría "${categoria.nombre}"?`)) return

  try {
    await categoriasService.updateEstado(categoria.id, nuevoEstado)
    toast.success(`Categoría ${nuevoEstado ? 'activada' : 'desactivada'}`)
    loadCategorias()
  } catch (error) {
  console.error('Error completo:', error)
  console.error('Respuesta del backend:', error.response?.data)
  toast.error('Error al actualizar el estado')
}
}

  return (
    <div>
      <Toaster position="top-right" />

      {/* Encabezado */}
      <div className={styles.header}>
        <h1 className={styles.title}>Categorías</h1>
        <button className={styles.addButton} onClick={handleCreate}>
          <Plus size={18} />
          Nueva categoría
        </button>
      </div>

      {/* Tabla */}
      {loading ? (
        <div className={styles.loading}>Cargando categorías...</div>
      ) : categorias.length === 0 ? (
        <div className={styles.empty}>No hay categorías registradas</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Descripción</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {categorias.map((cat) => (
              <tr key={cat.id}>
                <td>{cat.id}</td>
                <td>{cat.nombre}</td>
                <td>{cat.descripcion || '—'}</td>
                <td>
                  <span className={`${styles.badge} ${cat.activo ? styles.badgeActive : styles.badgeInactive}`}>
                    {cat.activo ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td>
                  <div className={styles.actions}>
                    <button className={styles.editButton} onClick={() => handleEdit(cat)}>
                      <Pencil size={16} />
                    </button>
                    <button
                      className={cat.activo ? styles.deleteButton : styles.activateButton}
                      onClick={() => handleToggleEstado(cat)}
                    >
                      {cat.activo ? 'Desactivar' : 'Activar'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Modal crear/editar */}
      {modalOpen && (
        <div className={styles.modalOverlay} onClick={() => setModalOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>
              {editing ? 'Editar categoría' : 'Nueva categoría'}
            </h2>

            <form className={styles.form} onSubmit={handleSave}>
              {formError && <div className={styles.error}>{formError}</div>}

              <div className={styles.inputGroup}>
                <label className={styles.label}>Nombre</label>
                <input
                  type="text"
                  className={styles.input}
                  placeholder="Ej: Pizzas Clásicas"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  required
                />
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Descripción</label>
                <textarea
                  className={`${styles.input} ${styles.textarea}`}
                  placeholder="Descripción breve de la categoría"
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                />
              </div>

              {editing && (
                <div className={styles.checkboxGroup}>
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    id="activo"
                    checked={formData.activo}
                    onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                  />
                  <label className={styles.label} htmlFor="activo">Categoría activa</label>
                </div>
              )}

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

export default Categorias