import api from "./api";

const pedidosService = {
  getAll() {
    return api.get("/pedidos/");
  },

  getByEstado(estado) {
    return api.get(`/pedidos/?estado=${estado}`);
  },

  getByMesa(mesaId) {
    return api.get(`/pedidos/?mesa=${mesaId}`);
  },

  getById(id) {
    return api.get(`/pedidos/${id}/`);
  },

  create(data) {
    return api.post("/pedidos/", data);
  },

  updateEstado(id, estado) {
    return api.patch(`/pedidos/${id}/estado/`, { estado });
  },

  delete(id) {
    return api.delete(`/pedidos/${id}/`);
  },
};

export default pedidosService;
