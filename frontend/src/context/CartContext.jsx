import { createContext, useContext, useState } from 'react'

const CartContext = createContext()

// Cada línea del carrito es un producto con una indicación: la misma pizza
// "sin albahaca" y sin indicación son líneas distintas
function lineaId(productoId, nota) {
  return `${productoId}::${nota}`
}

export function CartProvider({ children }) {
  const [items, setItems] = useState([])

  function addItem(producto, nota = '') {
    const notaLimpia = nota.trim()
    const id = lineaId(producto.id, notaLimpia)
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
  }

  function removeItem(id) {
    setItems(prev => prev.filter(item => item.lineaId !== id))
  }

  function updateQuantity(id, cantidad) {
    if (cantidad <= 0) {
      removeItem(id)
      return
    }
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
    <CartContext.Provider value={{ items, addItem, removeItem, updateQuantity, clearCart, getTotal, getTotalItems }}>
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
