import { AuthProvider } from './context/AuthContext'
import AppRouter from './routes/AppRouter'

// El carrito (CartProvider) vive en CartaLayout: es solo de la carta y va por mesa
function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  )
}

export default App
