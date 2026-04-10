import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth()

  // Mientras verifica el token, mostramos un loading
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        color: 'var(--color-text-secondary)'
      }}>
        Cargando...
      </div>
    )
  }

  // Si no hay usuario logueado, redirige al login
  if (!user) {
    return <Navigate to="/login" replace />
  }

  // Si hay roles permitidos y el usuario no tiene uno de ellos, redirige
  if (allowedRoles && !allowedRoles.includes(user.rol)) {
    return <Navigate to="/admin" replace />
  }

  // Si pasó todas las validaciones, muestra el contenido
  return children
}

export default ProtectedRoute