import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Minus, ShoppingCart, CheckCircle, ImageOff } from 'lucide-react'
import { useCart } from '../../context/CartContext'
import categoriasService from '../../services/categoriasService'
import productosService from '../../services/productosService'
import pedidosService from '../../services/pedidosService'
import toast, { Toaster } from 'react-hot-toast'
import styles from './CartaDigital.module.css'

function CartaDigital() {
  const [searchParams] = useSearchParams()
  const mesaId = searchParams.get('mesa')

  const [categorias, setCategorias] = useState([])
  const [productos, setProductos] = useState([])
  const [categoriaActiva, setCategoriaActiva] = useState(null)
  const [loading, setLoading] = useState(true)
  const [cartOpen, setCartOpen] = useState(false)
  const [sending, setSending] = useState(false)
  const [orderSent, setOrderSent] = useState(false)

  const { items, addItem, updateQuantity, clearCart, getTotal, getTotalItems } = useCart()

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (categoriaActiva) {
      loadProductosByCategoria(categoriaActiva)
    }
  }, [categoriaActiva])

  async function loadData() {
    try {
      const catRes = await categoriasService.getAll()
      const cats = catRes.data.filter(c => c.activo)
      setCategorias(cats)

      if (cats.length > 0) {
        setCategoriaActiva(cats[0].id)
      }
    } catch (error) {
      toast.error('Error al cargar el menú')
    } finally {
      setLoading(false)
    }
  }

  async function loadProductosByCategoria(catId) {
    try {
      const response = await productosService.getByCategoria(catId)
      setProductos(response.data.filter(p => p.disponible))
    } catch (error) {
      toast.error('Error al cargar productos')
    }
  }

  async function handleConfirmOrder() {
    if (!mesaId) {
      toast.error('No se detectó la mesa. Escanea el QR nuevamente.')
      return
    }
    if (items.length === 0) return

    setSending(true)
    try {
      await pedidosService.create({
        mesa_id: Number(mesaId),
        productos: items.map(item => ({
          producto_id: item.id,
          cantidad: item.cantidad,
        })),
      })
      clearCart()
      setCartOpen(false)
      setOrderSent(true)
    } catch (error) {
      toast.error('Error al enviar el pedido')
    } finally {
      setSending(false)
    }
  }

  function formatPrice(price) {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  function handleNewOrder() {
    setOrderSent(false)
  }

  if (loading) {
    return <div className={styles.loading}>Cargando menú...</div>
  }

  if (orderSent) {
    return (
      <div className={styles.successContainer}>
        <CheckCircle size={64} className={styles.successIcon} />
        <h2 className={styles.successTitle}>¡Pedido enviado!</h2>
        <p className={styles.successMessage}>
          Tu pedido fue recibido y está siendo preparado.
          <br />Te avisaremos cuando esté listo.
        </p>
        <button className={styles.newOrderButton} onClick={handleNewOrder}>
          Hacer otro pedido
        </button>
      </div>
    )
  }

  return (
    <div>
      <Toaster position="top-center" />

      {/* Tabs de categorías */}
      <div className={styles.categorias}>
        {categorias.map((cat) => (
          <button
            key={cat.id}
            className={`${styles.catButton} ${categoriaActiva === cat.id ? styles.catButtonActive : ''}`}
            onClick={() => setCategoriaActiva(cat.id)}
          >
            {cat.nombre}
          </button>
        ))}
      </div>

      {/* Lista de productos */}
      <div className={styles.productGrid}>
        {productos.length === 0 ? (
          <div className={styles.empty}>No hay productos disponibles</div>
        ) : (
          productos.map((prod) => (
            <div key={prod.id} className={styles.productCard}>
              {prod.imagen ? (
                <img src={prod.imagen} alt={prod.nombre} className={styles.productImage} />
              ) : (
                <div className={styles.noImage}>
                  <ImageOff size={24} />
                </div>
              )}
              <div className={styles.productInfo}>
                <div>
                  <div className={styles.productName}>{prod.nombre}</div>
                  {prod.descripcion && (
                    <div className={styles.productDesc}>{prod.descripcion}</div>
                  )}
                </div>
                <div className={styles.productFooter}>
                  <span className={styles.productPrice}>{formatPrice(prod.precio)}</span>
                  <button className={styles.addToCartButton} onClick={() => addItem(prod)}>
                    <Plus size={18} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Botón flotante del carrito */}
      {getTotalItems() > 0 && (
        <div className={styles.cartFloat} onClick={() => setCartOpen(true)}>
          <div className={styles.cartFloatLeft}>
            <span className={styles.cartBadge}>{getTotalItems()}</span>
            <span className={styles.cartFloatText}>Ver pedido</span>
          </div>
          <span className={styles.cartFloatTotal}>{formatPrice(getTotal())}</span>
        </div>
      )}

      {/* Modal del carrito */}
      {cartOpen && (
        <div className={styles.cartOverlay}>
          <div className={styles.cartModal}>
            <h2 className={styles.cartTitle}>Tu pedido</h2>

            {items.map((item) => (
              <div key={item.id} className={styles.cartItem}>
                <div className={styles.cartItemInfo}>
                  <div className={styles.cartItemName}>{item.nombre}</div>
                  <div className={styles.cartItemPrice}>{formatPrice(item.precio)} c/u</div>
                </div>
                <div className={styles.cartItemControls}>
                  <button
                    className={styles.qtyButton}
                    onClick={() => updateQuantity(item.id, item.cantidad - 1)}
                  >
                    <Minus size={14} />
                  </button>
                  <span className={styles.qtyValue}>{item.cantidad}</span>
                  <button
                    className={styles.qtyButton}
                    onClick={() => updateQuantity(item.id, item.cantidad + 1)}
                  >
                    <Plus size={14} />
                  </button>
                </div>
                <span className={styles.cartItemSubtotal}>
                  {formatPrice(item.precio * item.cantidad)}
                </span>
              </div>
            ))}

            <div className={styles.cartTotal}>
              <span className={styles.cartTotalLabel}>Total</span>
              <span className={styles.cartTotalValue}>{formatPrice(getTotal())}</span>
            </div>

            <div className={styles.cartActions}>
              <button
                className={styles.confirmButton}
                onClick={handleConfirmOrder}
                disabled={sending}
              >
                {sending ? 'Enviando pedido...' : 'Confirmar pedido'}
              </button>
              <button className={styles.closeCartButton} onClick={() => setCartOpen(false)}>
                Seguir viendo el menú
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CartaDigital