import api from "./api";

const usuariosService = {
  getAll() {
    return api.get("/auth/usuarios/");
  },

  create(data) {
    return api.post("/auth/usuarios/", data);
  },

  updateEstado(id, activo) {
    return api.patch(`/auth/usuarios/${id}/estado/`, { activo });
  },

  getRoles() {
    return api.get("/auth/roles/");
  },
};

export default usuariosService;
