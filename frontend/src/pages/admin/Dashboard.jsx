import { useState, useEffect } from 'react'
import { ClipboardList, Armchair, CreditCard, Pizza } from 'lucide-react'
import pedidosService from '../../services/pedidosService'
import mesasService from '../../services/mesasService'
import pagosService from '../../services/pagosService'
import productosService from '../../services/productosService'
import styles from './Dashboard.module.css'

function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    pedidosActivos: 0,
    mesasOcupadas: 0,
    ventasHoy: 0,
    totalProductos: 0,
  })
  const [pedidosRecientes, setPedidosRecientes] = useState([])
  const [mesas, setMesas] = useState([])

  useEffect(() => {
    loadDashboard()
  }, [])

  async function loadDashboard() {
    try {
      const [pedidosRes, mesasRes, pagosRes, productosRes] = await Promise.all([
        pedidosService.getAll(),
        mesasService.getAll(),
        pagosService.getAll(),
        productosService.getAll(),
      ])

      const pedidos = pedidosRes.data
      const mesasData = mesasRes.data
      const pagos = pagosRes.data
      const productos = productosRes.data

      // Pedidos activos (no entregados)
      const activos = pedidos.filter(p =>
        ['pendiente', 'en_preparacion', 'listo'].includes(p.estado)
      )

      // Mesas ocupadas
      const ocupadas = mesasData.filter(m => m.estado === 'ocupada')

      // Ventas de hoy (pagos completados)
      const hoy = new Date().toISOString().split('T')[0]
      const ventasHoy = pagos
        .filter(p => p.estado === 'completado' && p.fecha?.startsWith(hoy))
        .reduce((sum, p) => sum + Number(p.monto), 0)

      setStats({
        pedidosActivos: activos.length,
        mesasOcupadas: ocupadas.length,
        ventasHoy: ventasHoy,
        totalProductos: productos.length,
      })

      // Últimos 5 pedidos activos
      setPedidosRecientes(activos.slice(0, 5))

      // Estado de mesas
      setMesas(mesasData)
    } catch (error) {
      console.error('Error cargando dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  function formatPrice(price) {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(price)
  }

  function getEstadoBadge(estado) {
    const clases = {
      pendiente: styles.badgePendiente,
      en_preparacion: styles.badgeEnPreparacion,
      listo: styles.badgeListo,
    }
    const labels = {
      pendiente: 'Pendiente',
      en_preparacion: 'En preparación',
      listo: 'Listo',
    }
    return (
      <span className={`${styles.badge} ${clases[estado] || ''}`}>
        {labels[estado] || estado}
      </span>
    )
  }

  function getMesaBadge(estado) {
    const clases = {
      libre: styles.badgeLibre,
      ocupada: styles.badgeOcupada,
      reservada: styles.badgeReservada,
    }
    const labels = {
      libre: 'Libre',
      ocupada: 'Ocupada',
      reservada: 'Reservada',
    }
    return (
      <span className={`${styles.badge} ${clases[estado] || ''}`}>
        {labels[estado] || estado}
      </span>
    )
  }

  if (loading) {
    return <div className={styles.loading}>Cargando dashboard...</div>
  }

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>Dashboard</h1>
        <p className={styles.subtitle}>Resumen operativo de 400 Pizzería</p>
      </div>

      {/* Stats */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.statIconOrange}`}>
            <ClipboardList size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>{stats.pedidosActivos}</span>
            <span className={styles.statLabel}>Pedidos activos</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.statIconBlue}`}>
            <Armchair size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>{stats.mesasOcupadas}/{mesas.length}</span>
            <span className={styles.statLabel}>Mesas ocupadas</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.statIconGreen}`}>
            <CreditCard size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>{formatPrice(stats.ventasHoy)}</span>
            <span className={styles.statLabel}>Ventas de hoy</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={`${styles.statIcon} ${styles.statIconGold}`}>
            <Pizza size={24} />
          </div>
          <div className={styles.statInfo}>
            <span className={styles.statValue}>{stats.totalProductos}</span>
            <span className={styles.statLabel}>Productos en carta</span>
          </div>
        </div>
      </div>

      {/* Secciones */}
      <div className={styles.sections}>
        {/* Pedidos activos */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Pedidos activos</span>
          </div>
          <div className={styles.sectionBody}>
            {pedidosRecientes.length === 0 ? (
              <div className={styles.emptyList}>No hay pedidos activos</div>
            ) : (
              pedidosRecientes.map((pedido) => (
                <div key={pedido.id} className={styles.listItem}>
                  <div className={styles.listItemLeft}>
                    <span className={styles.listItemTitle}>
                      Pedido #{pedido.id} — Mesa {pedido.mesa?.numero || pedido.mesa_id}
                    </span>
                    <span className={styles.listItemSub}>
                      {pedido.detalles?.length || 0} productos
                    </span>
                  </div>
                  {getEstadoBadge(pedido.estado)}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Estado de mesas */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Estado de mesas</span>
          </div>
          <div className={styles.sectionBody}>
            {mesas.length === 0 ? (
              <div className={styles.emptyList}>No hay mesas registradas</div>
            ) : (
              mesas.map((mesa) => (
                <div key={mesa.id} className={styles.listItem}>
                  <div className={styles.listItemLeft}>
                    <span className={styles.listItemTitle}>Mesa {mesa.numero}</span>
                    <span className={styles.listItemSub}>Capacidad: {mesa.capacidad}</span>
                  </div>
                  {getMesaBadge(mesa.estado)}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard