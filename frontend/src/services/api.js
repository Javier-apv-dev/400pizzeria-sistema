import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor de REQUEST: agrega el token JWT a cada petición protegida
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Refresco en curso, compartido por todas las peticiones que reciban 401 a la vez
// (ej. el Promise.all del Dashboard). Con ROTATE_REFRESH_TOKENS el backend invalida
// el refresh token usado, así que solo puede enviarse una vez.
let refreshPromise = null;

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    throw new Error("No hay refresh token");
  }

  const response = await axios.post(
    "http://localhost:8000/api/auth/token/refresh/",
    {
      refresh: refreshToken,
    },
  );

  localStorage.setItem("access_token", response.data.access);
  // El backend rota el refresh token: hay que guardar el nuevo
  if (response.data.refresh) {
    localStorage.setItem("refresh_token", response.data.refresh);
  }
  return response.data.access;
}

// Interceptor de RESPONSE: si el token expiró (401), intenta refrescar
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Un 401 del login son credenciales incorrectas: se devuelve tal cual al formulario
    const esLogin = originalRequest?.url?.includes("/auth/login/");

    // Si recibimos 401 y no es un reintento, intentamos refrescar el token
    if (error.response?.status === 401 && !originalRequest._retry && !esLogin) {
      originalRequest._retry = true;

      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null;
          });
        }
        const newAccessToken = await refreshPromise;

        // Reintenta la petición original con el nuevo token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Si no se pudo refrescar, limpiamos todo y redirigimos al login
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export default api;
