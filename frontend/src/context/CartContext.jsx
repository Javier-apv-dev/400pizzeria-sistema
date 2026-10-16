import { createContext, useContext, useState, useEffect } from 'react'

const CartContext = createContext()

// El carrito se guarda en el navegador para sobrevivir a una recarga.
// Pasado este tiempo se descarta, para no revivir un pedido de otra visita.
const VIGENCIA_CARRITO_MS = 3 * 60 * 60 * 1000

function claveCarrito(mesa) {
  return `carrito-mesa-${mesa}`
}

function leerCarritoGuardado(mesa) {
  try {
    const guardado = JSON.parse(localStorage.getItem(claveCarrito(mesa)))
    if (!guardado || Date.now() - guardado.guardado > VIGENCIA_CARRITO_MS) return []
    return Array.isArray(guardado.items) ? guardado.items : []
  } catch {
    // Navegación privada, almacenamiento bloqueado o dato corrupto: carrito vacío
    return []
  }
}

// Cada línea del carrito es un producto con una indicación: la misma pizza
// "sin albahaca" y sin indicación son líneas distintas
function lineaId(productoId, nota) {
  return `${productoId}::${nota}`
}

// Mismos topes que valida el backend (apps/pedidos/serializers.py)
const CANTIDAD_MAX_POR_PRODUCTO = 20
const UNIDADES_MAX_POR_PEDIDO = 50

// Por qué no se puede sumar una unidad más a la línea, o null si se puede
function motivoLimite(items, id) {
  const linea = items.find(item => item.lineaId === id)
  if (linea && linea.cantidad >= CANTIDAD_MAX_POR_PRODUCTO) {
    return `Máximo ${CANTIDAD_MAX_POR_PRODUCTO} unidades por producto`
  }
  const unidades = items.reduce((sum, item) => sum + item.cantidad, 0)
  if (unidades >= UNIDADES_MAX_POR_PEDIDO) {
    return `Máximo ${UNIDADES_MAX_POR_PEDIDO} unidades por pedido`
  }
  return null
}

// Un carrito por mesa: CartaLayout lo monta con key={mesa}
export function CartProvider({ children, mesa }) {
  const [items, setItems] = useState(() => (mesa ? leerCarritoGuardado(mesa) : []))

  useEffect(() => {
    if (!mesa) return
    try {
      if (items.length === 0) {
        localStorage.removeItem(claveCarrito(mesa))
      } else {
        localStorage.setItem(claveCarrito(mesa), JSON.stringify({ guardado: Date.now(), items }))
      }
    } catch {
      // Si el navegador no permite guardar, el carrito sigue funcionando en memoria
    }
  }, [mesa, items])

  // Devuelve el motivo si no se pudo agregar (tope alcanzado), o null
  function addItem(producto, nota = '') {
    const notaLimpia = nota.trim()
    const id = lineaId(producto.id, notaLimpia)
    const motivo = motivoLimite(items, id)
    if (motivo) return motivo
    setItems(prev => {
      const existing = prev.find(item => item.lineaId === id)
      if (existing) {
        return prev.map(item =>
          item.lineaId === id
            ? { ...item, cantidad: item.cantidad + 1 }
            : item
        )
      }
      return [...prev, { ...producto, nota: notaLimpia, lineaId: id, cantidad: 1 }]
    })
    return null
  }

  function limiteAlcanzado(id) {
    return motivoLimite(items, id) !== null
  }

  function removeItem(id) {
    setItems(prev => prev.filter(item => item.lineaId !== id))
  }

  function updateQuantity(id, cantidad) {
    if (cantidad <= 0) {
      removeItem(id)
      return
    }
    const actual = items.find(item => item.lineaId === id)
    if (actual && cantidad > actual.cantidad && limiteAlcanzado(id)) return
    setItems(prev =>
      prev.map(item =>
        item.lineaId === id ? { ...item, cantidad } : item
      )
    )
  }

  function clearCart() {
    setItems([])
  }

  function getTotal() {
    return items.reduce((sum, item) => sum + item.precio * item.cantidad, 0)
  }

  function getTotalItems() {
    return items.reduce((sum, item) => sum + item.cantidad, 0)
  }

  return (
    <CartContext.Provider value={{ items, addItem, removeItem, updateQuantity, clearCart, getTotal, getTotalItems, limiteAlcanzado }}>
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error('useCart debe usarse dentro de CartProvider')
  }
  return context
}
