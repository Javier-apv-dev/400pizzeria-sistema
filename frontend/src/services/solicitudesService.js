import api from "./api";

const solicitudesService = {
  // Desde la carta (público): tipo "garzon" o "cuenta"
  crear(mesaId, tipo) {
    return api.post(`/mesas/${mesaId}/solicitudes/`, { tipo });
  },

  getPendientes() {
    return api.get("/solicitudes/?estado=pendiente");
  },

  atender(id) {
    return api.patch(`/solicitudes/${id}/atender/`);
  },
};

export default solicitudesService;
