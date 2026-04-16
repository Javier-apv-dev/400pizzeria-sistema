import api from "./api";

const categoriasService = {
  // Obtener todas las categorías
  getAll() {
    return api.get("/categorias/");
  },

  // Obtener una categoría por ID
  getById(id) {
    return api.get(`/categorias/${id}/`);
  },

  // Crear una nueva categoría
  create(data) {
    return api.post("/categorias/", data);
  },

  // Actualizar una categoría existente
  update(id, data) {
    return api.put(`/categorias/${id}/`, data);
  },

  delete(id) {
    return api.delete(`/categorias/${id}/`);
  },

  updateEstado(id, activo) {
    return api.patch(`/categorias/${id}/estado/`, { activo });
  },
};

export default categoriasService;
