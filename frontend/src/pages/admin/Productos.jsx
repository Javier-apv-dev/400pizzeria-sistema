import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, ImageOff } from 'lucide-react'
import productosService from '../../services/productosService'
import categoriasService from '../../services/categoriasService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './Productos.module.css'

const BACKEND_URL = 'http://localhost:8000'

function Productos() {
  // Estado del listado
  const [productos, setProductos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroCategoria, setFiltroCategoria] = useState('')

  // Estado del modal
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    precio: '',
    categoria_id: '',
    disponible: true,
  })
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // Cargar datos al montar
  useEffect(() => {
    loadData()
  }, [])

  // Recargar productos cuando cambia el filtro
  useEffect(() => {
    loadProductos()
  }, [filtroCategoria])

  async function loadData() {
    try {
      const [prodRes, catRes] = await Promise.all([
        productosService.getAll(),
        categoriasService.getAll(),
      ])
      setProductos(prodRes.data)
      setCategorias(catRes.data)
    } catch (error) {
      toast.error('Error al cargar los datos')
    } finally {
      setLoading(false)
    }
  }

  async function loadProductos() {
    try {
      const response = filtroCategoria
        ? await productosService.getByCategoria(filtroCategoria)
        : await productosService.getAll()
      setProductos(response.data)
    } catch (error) {
      toast.error('Error al cargar los productos')
    }
  }

  // Abrir modal para crear
  function handleCreate() {
    setEditing(null)
    setFormData({
      nombre: '',
      descripcion: '',
      precio: '',
      categoria_id: categorias.length > 0 ? categorias[0].id : '',
      disponible: true,
    })
    setImageFile(null)
    setImagePreview(null)
    setFormError('')
    setModalOpen(true)
  }

  // Abrir modal para editar
  function handleEdit(producto) {
    setEditing(producto)
    setFormData({
      nombre: producto.nombre,
      descripcion: producto.descripcion || '',
      precio: producto.precio,
      categoria_id: producto.categoria?.id || producto.categoria_id || '',
      disponible: producto.disponible,
    })
    setImageFile(null)
    setImagePreview(producto.imagen || null)
    setFormError('')
    setModalOpen(true)
  }

  // Manejar selección de imagen
  function handleImageChange(e) {
    const file = e.target.files[0]
    if (file) {
      setImageFile(file)
      setImagePreview(URL.createObjectURL(file))
    }
  }

  // Guardar (crear o editar)
  async function handleSave(e) {
    e.preventDefault()
    setFormError('')
    setSaving(true)

    try {
      // Construir FormData para enviar imagen + datos
      const data = new FormData()
      data.append('nombre', formData.nombre)
      data.append('descripcion', formData.descripcion)
      data.append('precio', formData.precio)
      data.append('categoria_id', formData.categoria_id)
      data.append('disponible', formData.disponible)
      if (imageFile) {
        data.append('imagen', imageFile)
      }

      if (editing) {
        await productosService.update(editing.id, data)
        toast.success('Producto actualizado')
      } else {
        await productosService.create(data)
        toast.success('Producto creado')
      }

      setModalOpen(false)
      loadProductos()
    } catch (error) {
      const errorData = error.response?.data
      const msg = errorData?.nombre?.[0] || errorData?.precio?.[0] || errorData?.detail || 'Error al guardar'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  // Eliminar
  async function handleDelete(producto) {
    if (!window.confirm(`¿Eliminar el producto "${producto.nombre}"?`)) return

    try {
      await productosService.delete(producto.id)
      toast.success('Producto eliminado')
      loadProductos()
    } catch (error) {
      toast.error('Error al eliminar el producto')
    }
  }

  // Formatear precio en CLP
  function formatPrice(price) {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  // Obtener nombre de categoría
  function getCategoryName(producto) {
    if (producto.categoria?.nombre) return producto.categoria.nombre
    const cat = categorias.find(c => c.id === producto.categoria_id)
    return cat?.nombre || '—'
  }

  return (
    <div>
      <Toaster position="top-right" />

      {/* Encabezado */}
      <div className={styles.header}>
        <h1 className={styles.title}>Productos</h1>
        <div className={styles.headerActions}>
          <select
            className={styles.filterSelect}
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
          >
            <option value="">Todas las categorías</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.nombre}</option>
            ))}
          </select>
          <button className={styles.addButton} onClick={handleCreate}>
            <Plus size={18} />
            Nuevo producto
          </button>
        </div>
      </div>

      {/* Tabla */}
      {loading ? (
        <div className={styles.loading}>Cargando productos...</div>
      ) : productos.length === 0 ? (
        <div className={styles.empty}>No hay productos registrados</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Imagen</th>
              <th>Nombre</th>
              <th>Categoría</th>
              <th>Precio</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {productos.map((prod) => (
              <tr key={prod.id}>
                <td>
                  {prod.imagen ? (
                    <img
                      src={prod.imagen}
                      alt={prod.nombre}
                      className={styles.productImage}
                    />
                  ) : (
                    <div className={styles.noImage}>
                      <ImageOff size={20} />
                    </div>
                  )}
                </td>
                <td>{prod.nombre}</td>
                <td>
                  <span className={`${styles.badge} ${styles.categoryBadge}`}>
                    {getCategoryName(prod)}
                  </span>
                </td>
                <td>
                  <span className={styles.price}>{formatPrice(prod.precio)}</span>
                </td>
                <td>
                  <span className={`${styles.badge} ${prod.disponible ? styles.badgeActive : styles.badgeInactive}`}>
                    {prod.disponible ? 'Disponible' : 'No disponible'}
                  </span>
                </td>
                <td>
                  <div className={styles.actions}>
                    <button className={styles.editButton} onClick={() => handleEdit(prod)}>
                      <Pencil size={16} />
                    </button>
                    <button className={styles.deleteButton} onClick={() => handleDelete(prod)}>
                      <Trash2 size={16} />
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
              {editing ? 'Editar producto' : 'Nuevo producto'}
            </h2>

            <form className={styles.form} onSubmit={handleSave}>
              {formError && <div className={styles.error}>{formError}</div>}

              <div className={styles.inputGroup}>
                <label className={styles.label}>Nombre</label>
                <input
                  type="text"
                  className={styles.input}
                  placeholder="Ej: Margherita"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  required
                />
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Descripción</label>
                <textarea
                  className={`${styles.input} ${styles.textarea}`}
                  placeholder="Ingredientes o descripción del producto"
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                />
              </div>

              <div className={styles.row}>
                <div className={styles.inputGroup}>
                  <label className={styles.label}>Precio (CLP)</label>
                  <input
                    type="number"
                    className={styles.input}
                    placeholder="9990"
                    value={formData.precio}
                    onChange={(e) => setFormData({ ...formData, precio: e.target.value })}
                    min="0"
                    step="10"
                    required
                  />
                </div>

                <div className={styles.inputGroup}>
                  <label className={styles.label}>Categoría</label>
                  <select
                    className={styles.select}
                    value={formData.categoria_id}
                    onChange={(e) => setFormData({ ...formData, categoria_id: e.target.value })}
                    required
                  >
                    <option value="">Seleccionar</option>
                    {categorias.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.nombre}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Imagen</label>
                <input
                  type="file"
                  className={styles.fileInput}
                  accept="image/*"
                  onChange={handleImageChange}
                />
                {imagePreview && (
                  <img src={imagePreview} alt="Preview" className={styles.imagePreview} />
                )}
              </div>

              {editing && (
                <div className={styles.checkboxGroup}>
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    id="disponible"
                    checked={formData.disponible}
                    onChange={(e) => setFormData({ ...formData, disponible: e.target.checked })}
                  />
                  <label className={styles.label} htmlFor="disponible">Producto disponible</label>
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

export default Productos