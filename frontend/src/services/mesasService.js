import api from "./api";

const mesasService = {
  getAll() {
    return api.get("/mesas/");
  },

  getById(id) {
    return api.get(`/mesas/${id}/`);
  },

  create(data) {
    return api.post("/mesas/", data);
  },

  update(id, data) {
    return api.put(`/mesas/${id}/`, data);
  },

  delete(id) {
    return api.delete(`/mesas/${id}/`);
  },

  updateEstado(id, estado) {
    return api.patch(`/mesas/${id}/estado/`, { estado });
  },

  regenerarQR(id) {
    return api.post(`/mesas/${id}/qr/`);
  },
};

export default mesasService;
