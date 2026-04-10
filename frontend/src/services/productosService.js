import api from "./api";

const productosService = {
  getAll() {
    return api.get("/productos/");
  },

  getByCategoria(categoriaId) {
    return api.get(`/productos/?categoria=${categoriaId}`);
  },

  getById(id) {
    return api.get(`/productos/${id}/`);
  },

  create(data) {
    return api.post("/productos/", data, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  update(id, data) {
    return api.put(`/productos/${id}/`, data, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  delete(id) {
    return api.delete(`/productos/${id}/`);
  },
};

export default productosService;
