import api from "./api";

const pagosService = {
  getAll() {
    return api.get("/pagos/");
  },

  getByEstado(estado) {
    return api.get(`/pagos/?estado=${estado}`);
  },

  getById(id) {
    return api.get(`/pagos/${id}/`);
  },

  create(data) {
    return api.post("/pagos/", data);
  },

  anular(id) {
    return api.patch(`/pagos/${id}/anular/`);
  },
};

export default pagosService;
