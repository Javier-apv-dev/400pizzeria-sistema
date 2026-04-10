import { useSearchParams } from 'react-router-dom'
import { Outlet } from 'react-router-dom'
import styles from './CartaLayout.module.css'

function CartaLayout() {
  const [searchParams] = useSearchParams()
  const mesa = searchParams.get('mesa')

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <img
          src="https://tofuu.getjusto.com/orioneat-local/resized2/Kra3Qq86eTHF5EhfY-300-x.webp"
          alt="400 Pizzería"
          className={styles.logo}
        />
        <h1 className={styles.title}>400 Pizzería</h1>
        {mesa && <p className={styles.mesaInfo}>Mesa {mesa}</p>}
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}

export default CartaLayout