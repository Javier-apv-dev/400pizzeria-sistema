import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import usuariosService from '../../services/usuariosService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Usuarios.module.css'

function Usuarios() {
  const [usuarios, setUsuarios] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)

  // Modal
  const [modalOpen, setModalOpen] = useState(false)
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    email: '',
    password: '',
    rol_id: '',
  })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        usuariosService.getAll(),
        usuariosService.getRoles(),
      ])
      setUsuarios(usersRes.data)
      setRoles(rolesRes.data)
    } catch (error) {
      toast.error('Error al cargar los datos')
    } finally {
      setLoading(false)
    }
  }

  function handleCreate() {
    setFormData({
      nombre: '',
      apellido: '',
      email: '',
      password: '',
      rol_id: roles.length > 0 ? roles[0].id : '',
    })
    setFormError('')
    setModalOpen(true)
  }

  async function handleSave(e) {
    e.preventDefault()
    setFormError('')
    setSaving(true)

    try {
      await usuariosService.create(formData)
      toast.success('Usuario creado')
      setModalOpen(false)
      loadData()
    } catch (error) {
      const data = error.response?.data
      const msg = data?.email?.[0] || data?.password?.[0] || data?.detail || 'Error al crear el usuario'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleEstado(usuario) {
    const nuevoEstado = !usuario.activo
    const accion = nuevoEstado ? 'activar' : 'desactivar'
    if (!window.confirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} a ${usuario.nombre} ${usuario.apellido}?`)) return

    try {
      await usuariosService.updateEstado(usuario.id, nuevoEstado)
      toast.success(`Usuario ${nuevoEstado ? 'activado' : 'desactivado'}`)
      loadData()
    } catch (error) {
      toast.error('Error al actualizar el estado')
    }
  }

  function getRolName(usuario) {
    if (usuario.rol?.nombre) return usuario.rol.nombre
    const rol = roles.find(r => r.id === usuario.rol_id)
    return rol?.nombre || '—'
  }

  return (
    <div>
      <Toaster position="top-right" />

      <div className={styles.header}>
        <h1 className={styles.title}>Usuarios</h1>
        <button className={styles.addButton} onClick={handleCreate}>
          <Plus size={18} />
          Nuevo usuario
        </button>
      </div>

      {loading ? (
        <div className={styles.loading}>Cargando usuarios...</div>
      ) : usuarios.length === 0 ? (
        <div className={styles.empty}>No hay usuarios registrados</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Email</th>
              <th>Rol</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.nombre} {user.apellido}</td>
                <td>{user.email}</td>
                <td>
                  <span className={`${styles.badge} ${styles.rolBadge}`}>
                    {getRolName(user)}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${user.activo ? styles.badgeActive : styles.badgeInactive}`}>
                    {user.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td>
                  <button
                    className={user.activo ? styles.deleteButton : styles.activateButton}
                    onClick={() => handleToggleEstado(user)}
                  >
                    {user.activo ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Modal crear usuario */}
      {modalOpen && (
        <div className={styles.modalOverlay} onClick={() => setModalOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>Nuevo usuario</h2>

            <form className={styles.form} onSubmit={handleSave}>
              {formError && <div className={styles.error}>{formError}</div>}

              <div className={styles.row}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Nombre</label>
                  <input
                    type="text"
                    className={styles.input}
                    placeholder="Nombre"
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    required
                  />
                </div>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Apellido</label>
                  <input
                    type="text"
                    className={styles.input}
                    placeholder="Apellido"
                    value={formData.apellido}
                    onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Correo electrónico</label>
                <input
                  type="email"
                  className={styles.input}
                  placeholder="correo@400pizzeria.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Contraseña</label>
                <input
                  type="password"
                  className={styles.input}
                  placeholder="Mínimo 8 caracteres"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  minLength={8}
                />
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Rol</label>
                <select
                  className={styles.select}
                  value={formData.rol_id}
                  onChange={(e) => setFormData({ ...formData, rol_id: e.target.value })}
                  required
                >
                  {roles.map((rol) => (
                    <option key={rol.id} value={rol.id}>{rol.nombre}</option>
                  ))}
                </select>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelButton} onClick={() => setModalOpen(false)}>
                  Cancelar
                </button>
                <button type="submit" className={styles.saveButton} disabled={saving}>
                  {saving ? 'Creando...' : 'Crear usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Usuarios