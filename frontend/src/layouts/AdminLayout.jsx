import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard,
  Users,
  Pizza,
  Tag,
  Armchair,
  ClipboardList,
  CreditCard,
  LogOut,
  Menu,
  X
} from 'lucide-react'
import styles from './AdminLayout.module.css'

const navItems = [
  { to: '/admin', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/admin/usuarios', icon: Users, label: 'Usuarios', roles: ['Administrador'] },
  { to: '/admin/categorias', icon: Tag, label: 'Categorías', roles: ['Administrador'] },
  { to: '/admin/productos', icon: Pizza, label: 'Productos', roles: ['Administrador'] },
  { to: '/admin/mesas', icon: Armchair, label: 'Mesas', roles: ['Administrador', 'Garzon'] },
  { to: '/admin/pedidos', icon: ClipboardList, label: 'Pedidos' },
  { to: '/admin/pagos', icon: CreditCard, label: 'Pagos', roles: ['Administrador', 'Cajero', 'Garzon'] },
]

function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  // Filtra las opciones del menú según el rol del usuario
  const filteredNav = navItems.filter(item => {
    if (!item.roles) return true
    return item.roles.includes(user?.rol?.nombre)
  })

  return (
    <div className={styles.layout}>
      {/* Overlay móvil */}
      {sidebarOpen && (
        <div className={styles.overlay} onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.sidebarHeader}>
          <img
            src="https://tofuu.getjusto.com/orioneat-local/resized2/Kra3Qq86eTHF5EhfY-300-x.webp"
            alt="400 Pizzería"
            className={styles.logo}
          />
          <span className={styles.brandName}>400 Pizzería</span>
          {/* Botón cerrar en móvil */}
          <button
            className={styles.menuButton}
            onClick={() => setSidebarOpen(false)}
            style={{ marginLeft: 'auto', display: sidebarOpen ? 'block' : 'none' }}
          >
            <X size={20} />
          </button>
        </div>

        <nav className={styles.nav}>
          {filteredNav.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
              }
              onClick={() => setSidebarOpen(false)}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <div>
              <div className={styles.userName}>{user?.nombre} {user?.apellido}</div>
              <div className={styles.userRole}>{user?.rol?.nombre}</div>
            </div>
          </div>
          <button className={styles.logoutButton} onClick={handleLogout}>
            <LogOut size={16} />
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Contenido principal */}
      <main className={styles.main}>
        <div className={styles.topBar}>
          <button className={styles.menuButton} onClick={() => setSidebarOpen(true)}>
            <Menu size={24} />
          </button>
          <img
            src="https://tofuu.getjusto.com/orioneat-local/resized2/Kra3Qq86eTHF5EhfY-300-x.webp"
            alt="400 Pizzería"
            className={styles.topBarLogo}
          />
          <div style={{ width: 24 }} />
        </div>

        <Outlet />
      </main>
    </div>
  )
}

export default AdminLayout