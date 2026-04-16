import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from '../pages/Login'
import CartaDigital from '../pages/carta/CartaDigital'
import Dashboard from '../pages/admin/Dashboard'
import Categorias from '../pages/admin/Categorias'
import AdminLayout from '../layouts/AdminLayout'
import ProtectedRoute from './ProtectedRoute'
import Productos from '../pages/admin/Productos'
import Mesas from '../pages/admin/Mesas'
import Pedidos from '../pages/admin/Pedidos'
import Pagos from '../pages/admin/Pagos'
import Usuarios from '../pages/admin/Usuarios'
import CartaLayout from '../layouts/CartaLayout'

function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route path="/login" element={<Login />} />
        <Route path="/carta" element={<CartaLayout />}>
          <Route index element={<CartaDigital />} />
        </Route>

        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="categorias" element={<Categorias />} />
          <Route path="productos" element={<Productos />} />
          <Route path="mesas" element={<Mesas />} />
          <Route path="pedidos" element={<Pedidos />} />
          <Route path="pagos" element={<Pagos />} />
          <Route path="usuarios" element={<Usuarios />} />
        </Route>

        <Route path="*" element={<h1>404 — Página no encontrada</h1>} />
      </Routes>
    </BrowserRouter>
  )
}

export default AppRouter