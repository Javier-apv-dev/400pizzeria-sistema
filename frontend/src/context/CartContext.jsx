import { createContext, useContext, useState } from 'react'

const CartContext = createContext()

export function CartProvider({ children }) {
  const [items, setItems] = useState([])

  function addItem(producto) {
    setItems(prev => {
      const existing = prev.find(item => item.id === producto.id)
      if (existing) {
        return prev.map(item =>
          item.id === producto.id
            ? { ...item, cantidad: item.cantidad + 1 }
            : item
        )
      }
      return [...prev, { ...producto, cantidad: 1 }]
    })
  }

  function removeItem(productoId) {
    setItems(prev => prev.filter(item => item.id !== productoId))
  }

  function updateQuantity(productoId, cantidad) {
    if (cantidad <= 0) {
      removeItem(productoId)
      return
    }
    setItems(prev =>
      prev.map(item =>
        item.id === productoId ? { ...item, cantidad } : item
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