# Catálogo de casos de prueba — 400 Pizzería

Casos de prueba funcionales y no funcionales del sistema. Los ejecutan los QA testers sobre el sistema completo: carta digital y panel administrativo.

Este catálogo forma parte del plan de aseguramiento de la calidad (sección 3.8 de la memoria). Sus resultados van al Anexo A. Los identificadores de requerimientos (RF01 a RF41, RNF1 a RNF7) corresponden a la matriz de trazabilidad v2 de la memoria. Las pruebas automatizadas de la API están en los `tests.py` de cada app; hoy son 113.

- **Versión del catálogo:** 1.1, del 18 de octubre de 2026 (comandos del entorno de prueba y primeros defectos registrados).
- **Sistema bajo prueba:** rama `main` desde el commit `74c2adf`.

## Cómo usar este catálogo

1. **Entorno.**
   - El backend se ejecuta con una base de datos de prueba, **nunca con la base real**: desde `backend/`, `python manage.py runserver --settings=config.settings_qa`. El frontend se abre en `http://localhost:5173`.
   - Para usar la carta desde un teléfono, ambos equipos deben estar en la misma red, y la dirección del computador debe estar configurada como indica el README.
2. **Datos.** Antes de empezar, se carga el conjunto de datos de prueba de la sección siguiente con `python manage.py cargar_datos_qa --settings=config.settings_qa`. El comando deja la base en su estado inicial, así que también sirve para repetir un caso desde cero.
3. **Ejecución.** Cada caso se ejecuta en orden, siguiendo sus pasos. Al terminarlo se marca el resultado:
   - **Aprobado:** todo lo esperado ocurrió.
   - **Fallido:** algo no ocurrió o ocurrió distinto.
   - **Bloqueado:** no se pudo ejecutar por un fallo anterior.
   - **No aplica.**
4. **Evidencia.** Se guarda una captura por caso con el nombre `<ID>_<fecha>.png`, por ejemplo `CF-06_2026-10-25.png`.
5. **Defectos.** Si un caso falla, se registra el defecto en la última sección, con la captura y los pasos para repetirlo.
6. **Limitaciones conocidas.** Las limitaciones L1 a L6 de la matriz de trazabilidad no se informan como defectos. Por ejemplo, que un rol inexistente enviado directo a la API responda 500.

## Datos de prueba

| Tipo | Datos |
|---|---|
| Usuarios | `admin@qa.cl` (Administrador), `garzon@qa.cl` (Garzón), `cocina@qa.cl` (Cocina). Las contraseñas las entrega el responsable de QA; no se publican aquí |
| Categorías | Pizzas (activa), Bebidas (activa), Postres (**inactiva**) |
| Productos | Margherita $9.990 (Pizzas, disponible, con imagen) · Diavola $11.990 (Pizzas, disponible) · Capricciosa $10.990 (Pizzas, **no disponible**) · Coca-Cola $1.990 (Bebidas, disponible) · Tiramisú $4.990 (Postres, disponible, pero su categoría está inactiva) |
| Mesas | Mesa 1 (capacidad 4), Mesa 2 (capacidad 2), Mesa 3 (capacidad 6), Mesa 4 (capacidad 4), todas libres y con su QR |

## Casos de uso cubiertos

| Caso de uso | Actor | Casos |
|---|---|---|
| CU-01 Ver la carta de la mesa | Cliente | CF-01, CF-02 |
| CU-02 Armar el pedido | Cliente | CF-03, CF-04, CF-05 |
| CU-03 Enviar el pedido | Cliente | CF-06 |
| CU-04 Llamar al garzón o pedir la cuenta | Cliente | CF-07 |
| CU-05 Iniciar y cerrar sesión | Personal | CF-08, CF-09, CF-10, CF-11 |
| CU-06 Gestionar usuarios | Administrador | CF-12 |
| CU-07 Gestionar categorías | Administrador | CF-13 |
| CU-08 Gestionar productos | Administrador | CF-14, CF-15, CF-16 |
| CU-09 Gestionar mesas y códigos QR | Administrador y Garzón | CF-17, CF-18, CF-19 |
| CU-10 Preparar pedidos | Cocina | CF-20, CF-22 |
| CU-11 Entregar pedidos | Garzón | CF-21 |
| CU-12 Eliminar un pedido pendiente | Administrador | CF-23 |
| CU-13 Atender avisos de mesa | Garzón y Administrador | CF-24 |
| CU-14 Cobrar, anular y eliminar pagos | Garzón y Administrador | CF-25, CF-26, CF-27, CF-28 |
| CU-15 Ver el resumen del día | Personal | CF-29 |

Al final de cada caso se completa este bloque:

> **Resultado:** ☐ Aprobado ☐ Fallido ☐ Bloqueado ☐ No aplica · **Evidencia:** ____ · **Ejecutado por:** ____ · **Fecha:** ____ · **Navegador y dispositivo:** ____

---

## Casos funcionales

### CF-01 · Abrir la carta desde el QR de una mesa
**CU-01** · **RF13, RF15, RF16, RF38** · **Rol:** cliente, sin sesión

- **Precondiciones:** datos de prueba cargados; QR de la Mesa 1 a mano (descargado desde el panel o en pantalla).
- **Pasos:**
  1. Escanear el QR de la Mesa 1 con la cámara del teléfono y abrir el enlace.
  2. Revisar la cabecera, las pestañas de categorías y los productos.
  3. Tocar la pestaña Bebidas.
- **Resultado esperado:**
  - se abre la carta sin pedir cuenta ni contraseña;
  - la cabecera dice «Mesa 1»;
  - aparecen solo las pestañas Pizzas y Bebidas; Postres no aparece porque está inactiva;
  - en Pizzas se ven Margherita y Diavola con imagen (o ícono si no tiene), descripción y precio en pesos; Capricciosa no aparece porque no está disponible;
  - en Bebidas aparece Coca-Cola.

### CF-02 · QR de una mesa que no existe
**CU-01** · **RF38** · **Rol:** cliente

- **Pasos:** abrir en el navegador `http://localhost:5173/carta?mesa=999`.
- **Resultado esperado:**
  - la cabecera muestra «No encontramos esta mesa. Escanea de nuevo el código QR o pide ayuda al personal.»;
  - no aparecen los botones «Llamar al garzón» ni «Pedir la cuenta».

### CF-03 · Agregar productos con y sin indicaciones
**CU-02** · **RF16, RF30** · **Rol:** cliente

- **Precondiciones:** carta de la Mesa 1 abierta y carrito vacío.
- **Pasos:**
  1. Tocar la tarjeta de Margherita para abrir su detalle.
  2. En «Indicaciones para la cocina (opcional)», escribir `sin albahaca` y tocar «Agregar».
  3. Tocar el botón **+** de la tarjeta de Margherita, que la agrega sin indicación.
  4. Tocar la barra «Ver pedido».
- **Resultado esperado:**
  - la barra muestra 2 productos y $19.980;
  - en «Tu pedido» hay **dos líneas** de Margherita: una con la indicación «sin albahaca» y otra sin indicación, cada una con cantidad 1;
  - el total es $19.980.

### CF-04 · Topes de cantidad
**CU-02** · **RF36** · **Rol:** cliente

- **Pasos:**
  1. En «Tu pedido», tocar el **+** de una línea hasta llegar a 20 unidades.
  2. Intentar agregar una unidad más a esa línea.
  3. Agregar otros productos hasta sumar 50 unidades en total e intentar agregar uno más desde la carta.
- **Resultado esperado:**
  - al llegar a 20 unidades, el **+** de esa línea queda deshabilitado;
  - al llegar a 50 unidades en total, la carta muestra «Máximo 50 unidades por pedido» y no agrega más.

### CF-05 · El carrito se conserva al recargar
**CU-02** · **RF37** · **Rol:** cliente

- **Pasos:**
  1. En la Mesa 1, agregar Diavola y Coca-Cola.
  2. Recargar la página.
  3. Abrir la carta de la Mesa 2 (`/carta?mesa=<id de la Mesa 2>`).
- **Resultado esperado:**
  - tras recargar, la barra sigue mostrando 2 productos y el carrito tiene los mismos productos;
  - la carta de la Mesa 2 parte con su propio carrito vacío.

### CF-06 · Enviar el pedido en 5 interacciones o menos
**CU-03** · **RF17, RF18, RF19, RNF2** · **Rol:** cliente; después, Garzón en el panel

- **Precondiciones:** carta de la Mesa 1 abierta y carrito vacío; Mesa 1 libre.
- **Pasos:** contar cada toque.
  1. Tocar el **+** de Margherita.
  2. Tocar «Ver pedido».
  3. Tocar «Confirmar pedido».
  4. En otro equipo, entrar al panel como Garzón y abrir Pedidos y Mesas.
- **Resultado esperado:**
  - aparece «¡Pedido enviado!» después de **5 toques o menos** (anotar cuántos fueron);
  - en el panel aparece el pedido de la Mesa 1 con Margherita × 1, total $9.990 y estado Pendiente;
  - la Mesa 1 figura como Ocupada.

### CF-07 · Llamar al garzón y pedir la cuenta
**CU-04** · **RF33** · **Rol:** cliente; después, Garzón en el panel

- **Pasos:**
  1. En la carta de la Mesa 1, tocar «Llamar al garzón».
  2. Tocar «Pedir la cuenta».
  3. Recargar la carta y tocar de nuevo «Llamar al garzón».
  4. Revisar el panel del Garzón (aviso en la parte superior).
- **Resultado esperado:**
  - cada botón cambia a «Avisado, ya viene» y queda deshabilitado durante un minuto;
  - en el panel hay **dos avisos** de la Mesa 1: «Llamar al garzón» y «Pedir la cuenta»;
  - repetir el llamado (paso 3) **no** crea un tercer aviso.

### CF-08 · Iniciar sesión con credenciales válidas
**CU-05** · **RF01, RF02** · **Rol:** Administrador, Garzón y Cocina

- **Pasos:**
  1. Abrir `http://localhost:5173/login`.
  2. Ingresar el correo y la contraseña del usuario y tocar «Ingresar».
- **Resultado esperado:** se abre el Dashboard, y la esquina inferior del menú muestra el nombre y el rol del usuario.

### CF-09 · Credenciales incorrectas y usuario desactivado
**CU-05** · **RF01** · **Rol:** personal

- **Pasos:**
  1. Intentar ingresar con `garzon@qa.cl` y una contraseña incorrecta.
  2. El Administrador desactiva al Garzón (ver CF-12). Después, intentar ingresar con la contraseña correcta del Garzón.
- **Resultado esperado:**
  - en ambos casos aparece «Credenciales incorrectas» y no se entra al panel;
  - el sistema no distingue al usuario desactivado (issue `#14`); no se informa como defecto.

### CF-10 · Cerrar sesión y proteger el panel
**CU-05** · **RF04, RNF1** · **Rol:** personal

- **Pasos:**
  1. Con la sesión iniciada, tocar «Cerrar sesión».
  2. Escribir `http://localhost:5173/admin` en la barra de direcciones.
- **Resultado esperado:** tras cerrar la sesión se vuelve a la pantalla de inicio de sesión, y al intentar abrir `/admin` sin sesión también se redirige ahí.

### CF-11 · El menú y los datos dependen del rol
**CU-05** · **RF07, RNF1** · **Rol:** Administrador, Garzón y Cocina

- **Pasos:**
  1. Ingresar con cada rol y revisar el menú lateral.
  2. Como Garzón, escribir `http://localhost:5173/admin/usuarios` en la barra de direcciones.
- **Resultado esperado:**
  - **Administrador** ve Dashboard, Usuarios, Categorías, Productos, Mesas, Pedidos y Pagos;
  - **Garzón** ve Dashboard, Mesas, Pedidos y Pagos;
  - **Cocina** ve Dashboard y Pedidos;
  - en el paso 2, el Garzón **no ve la lista de usuarios**: aparece un mensaje de error de carga.

### CF-12 · Crear, editar, desactivar y reactivar un usuario
**CU-06** · **RF05, RF06** · **Rol:** Administrador

- **Pasos:**
  1. En Usuarios, tocar «Nuevo usuario» y completar:
     - nombre `Ana`, apellido `Rojas`, correo `ana@qa.cl`;
     - una contraseña de 8 caracteres o más;
     - rol Cocina.

     Luego tocar «Crear usuario».
  2. Editar a Ana: cambiar el nombre a `Ana María` y tocar «Guardar cambios».
  3. Desactivar a Ana y confirmar.
  4. Intentar ingresar como Ana en otra ventana privada.
  5. Reactivar a Ana e ingresar de nuevo.
- **Resultado esperado:**
  - aparecen «Usuario creado» y «Usuario actualizado», y la tabla muestra el rol Cocina y el estado correspondiente;
  - desactivada, Ana no puede entrar; reactivada, sí.
- **Observación O1:** el formulario exige al menos 8 caracteres, aunque la API acepta 6.

### CF-13 · Crear, editar, desactivar y activar una categoría
**CU-07** · **RF08** · **Rol:** Administrador

- **Pasos:**
  1. En Categorías, tocar «Nueva categoría», escribir `Promociones` y guardar.
  2. Editar su descripción.
  3. Desactivarla y confirmar.
  4. Revisar la carta de la Mesa 1.
  5. Activarla y revisar la carta de nuevo.
- **Resultado esperado:**
  - aparecen «Categoría creada» y «Categoría actualizada»;
  - mientras está inactiva, la pestaña Promociones no aparece en la carta; al activarla, sí aparece.

### CF-14 · Crear un producto con imagen
**CU-08** · **RF09, RF10** · **Rol:** Administrador

- **Pasos:**
  1. En Productos, tocar «Nuevo producto» y completar:
     - nombre `Napolitana`, descripción `Tomate, anchoas y aceitunas`;
     - precio `10490`, categoría Pizzas;
     - una imagen JPG o PNG (revisar la vista previa).

     Luego guardar.
  2. Abrir la carta de la Mesa 1, en la pestaña Pizzas.
- **Resultado esperado:**
  - aparece «Producto creado» y el producto figura en la tabla con su categoría;
  - en la carta aparece Napolitana con su imagen, descripción y $10.490.

### CF-15 · Validaciones al crear un producto
**CU-08** · **RF09** · **Rol:** Administrador

- **Pasos:**
  1. Intentar crear un producto con precio `0`.
  2. Intentar crear un producto adjuntando un archivo que no sea imagen, por ejemplo un PDF renombrado.
- **Resultado esperado:** en ambos casos el formulario muestra un error y el producto no se crea.

### CF-16 · Disponibilidad y eliminación de un producto
**CU-08** · **RF11** · **Rol:** Administrador

- **Pasos:**
  1. Editar Diavola, desmarcar «Producto disponible» y guardar.
  2. Revisar la carta.
  3. Eliminar Coca-Cola con el ícono del tacho y confirmar.
  4. En Productos, usar el filtro «No disponibles».
- **Resultado esperado:**
  - Diavola y Coca-Cola dejan de aparecer en la carta;
  - en el panel siguen existiendo y aparecen con el filtro «No disponibles», porque eliminar es un borrado lógico.

### CF-17 · Crear una mesa con QR y usarlo
**CU-09** · **RF12, RF13** · **Rol:** Administrador

- **Pasos:**
  1. En Mesas, tocar «Nueva mesa», con número `5` y capacidad `4`, y guardar.
  2. Tocar «Descargar» en la tarjeta de la Mesa 5.
  3. Escanear el QR descargado con un teléfono.
- **Resultado esperado:**
  - aparece «Mesa creada con código QR» y la tarjeta muestra el QR;
  - se descarga un archivo PNG;
  - al escanearlo se abre la carta con la cabecera «Mesa 5».

### CF-18 · Número repetido y mesa con pedidos
**CU-09** · **RF12** · **Rol:** Administrador

- **Precondiciones:** la Mesa 1 tiene al menos un pedido (por ejemplo, el de CF-06).
- **Pasos:**
  1. Intentar crear una mesa con el número `1`.
  2. Intentar eliminar la Mesa 1 y confirmar.
- **Resultado esperado:**
  - en el paso 1, el formulario muestra un error por número repetido;
  - en el paso 2 aparece «La mesa 1 tiene pedidos registrados y no se puede eliminar» y la mesa se conserva.

### CF-19 · El Garzón cambia el estado de una mesa
**CU-09** · **RF14, RF07** · **Rol:** Garzón

- **Pasos:**
  1. En Mesas, cambiar el estado de la Mesa 3 a Reservada con el selector.
  2. Revisar qué botones aparecen.
- **Resultado esperado:**
  - el estado cambia y se muestra un aviso de confirmación;
  - el Garzón **no** ve los botones para crear, editar, eliminar ni regenerar el QR;
  - **sí** ve «Descargar», que solo baja la imagen del QR.

### CF-20 · La cocina recibe y prepara un pedido
**CU-10** · **RF20, RF22, RF24, RF30, RF31, RF35** · **Rol:** Cocina; un cliente en la carta

- **Precondiciones:** Cocina en Pedidos (vista «Activos»), después de haber hecho al menos un clic en la página. Los navegadores solo dejan sonar una página después de un clic.
- **Pasos:**
  1. El cliente envía desde la Mesa 2 un pedido de Margherita con la indicación `bien cocida`.
  2. Esperar como máximo 10 segundos en la pantalla de la cocina.
  3. Tocar «Preparar» y luego «Marcar listo».
- **Resultado esperado:**
  - el pedido aparece en 10 segundos o menos, **suena un aviso** y la indicación se ve destacada;
  - la tarjeta muestra el detalle (producto, cantidad, subtotal y total) y el tiempo en el estado;
  - tras cada paso, el estado cambia y el seguimiento muestra la hora de cada etapa;
  - la cocina **no** ve el botón «Entregar».

### CF-21 · El Garzón entrega y la mesa se libera
**CU-11** · **RF21, RF41** · **Rol:** Garzón

- **Precondiciones:** pedido de la Mesa 2 en estado Listo y sin otros pedidos activos en esa mesa.
- **Pasos:**
  1. Tocar «Entregar».
  2. Revisar Mesas.
- **Resultado esperado:**
  - el pedido queda Entregado («Pedido completado») y sale de la vista «Activos»;
  - la Mesa 2 vuelve a Libre.

### CF-22 · Alertas por tiempo en el estado
**CU-10** · **RF32** · **Rol:** Cocina o Garzón

- **Pasos:**
  1. Dejar un pedido en estado Pendiente sin avanzarlo.
  2. Revisar su tarjeta a los 15 minutos y a los 25 minutos.
- **Resultado esperado:**
  - el tiempo se muestra como «Recibido hace X min»;
  - desde los 15 minutos se ve en color ámbar y desde los 25, en rojo.

### CF-23 · Eliminar un pedido pendiente
**CU-12** · **RF23** · **Rol:** Administrador

- **Pasos:**
  1. En Pedidos, eliminar un pedido Pendiente con el ícono del tacho y confirmar.
  2. Buscar el ícono en un pedido En preparación.
- **Resultado esperado:**
  - aparece «Pedido eliminado»;
  - el ícono de eliminar solo aparece en los pedidos pendientes.

### CF-24 · Atender los avisos de las mesas
**CU-13** · **RF34, RF35** · **Rol:** Garzón; Cocina para comparar

- **Precondiciones:** avisos pendientes de CF-07.
- **Pasos:**
  1. Como Garzón, revisar el aviso «Mesa 1 · Pedir la cuenta».
  2. Tocar «Cobrar».
  3. Volver y tocar «Atender» en ambos avisos.
  4. Ingresar como Cocina.
- **Resultado esperado:**
  - el aviso aparece arriba de cualquier pantalla del panel y suena al llegar;
  - «Cobrar» lleva a Pagos;
  - al atenderlos, los avisos desaparecen;
  - la Cocina no ve avisos de mesa.

### CF-25 · Registrar un pago
**CU-14** · **RF25, RF26, RF27** · **Rol:** Garzón

- **Precondiciones:** un pedido Entregado sin pago, por ejemplo el de CF-21.
- **Pasos:**
  1. En Pagos, tocar «Registrar pago».
  2. Elegir el pedido, revisar el detalle y el «Total a cobrar», y elegir Débito.
  3. Tocar «Registrar pago».
- **Resultado esperado:**
  - aparece «Pago registrado»;
  - la tabla muestra el pedido, la mesa, Débito, el monto igual al total, estado Completado y el nombre del Garzón en «Registrado por»;
  - el pedido ya no se ofrece para cobrar.

### CF-26 · Anular un pago y volver a cobrar
**CU-14** · **RF39** · **Rol:** Garzón

- **Pasos:**
  1. Anular el pago de CF-25 y confirmar.
  2. Tocar «Registrar pago».
  3. Cobrar de nuevo ese pedido en Efectivo.
- **Resultado esperado:**
  - aparece «Pago anulado» y la fila muestra «Anulado por» con el nombre del Garzón;
  - el pedido vuelve a ofrecerse para cobrar y el nuevo pago queda Completado.

### CF-27 · Eliminar un pago anulado
**CU-14** · **RF39** · **Rol:** Garzón y Administrador

- **Pasos:**
  1. Como Garzón, buscar la opción «Eliminar» en el pago anulado.
  2. Como Administrador, eliminar ese pago y confirmar.
- **Resultado esperado:**
  - el Garzón no ve «Eliminar»;
  - el Administrador sí, solo en los pagos anulados, y al usarla aparece «Pago eliminado».

### CF-28 · Historial de pagos por estado
**CU-14** · **RF28** · **Rol:** Garzón o Administrador

- **Pasos:** usar los filtros «Todos», «Completados» y «Anulados».
- **Resultado esperado:** cada filtro muestra solo los pagos de ese estado, del más reciente al más antiguo. El filtro por fecha no existe (limitación L4).

### CF-29 · Resumen del día en el Dashboard
**CU-15** · **RF29, RF40** · **Rol:** Administrador y Cocina

- **Pasos:**
  1. Como Administrador, abrir el Dashboard después de los casos anteriores.
  2. Ingresar como Cocina y abrir el Dashboard.
- **Resultado esperado:**
  - el Administrador ve:
    - Pedidos activos;
    - Mesas ocupadas, como «ocupadas/total»;
    - Ventas de hoy, igual a la suma de los pagos completados de hoy;
    - Productos en carta (disponibles de categorías activas);
    - Preparación promedio hoy, en minutos;
  - la Cocina ve el resumen **sin** la tarjeta Ventas de hoy.

---

## Casos no funcionales

### CNF-01 · Sesión y permisos en el navegador
**RNF1** · Complementa la matriz de permisos automatizada (`config/tests.py`, 4 perfiles × 40 combinaciones).

- **Pasos:**
  1. Como Garzón, abrir las herramientas de desarrollo (F12), pestaña Red, y entrar a `/admin/usuarios`.
  2. Revisar la respuesta de la petición a `/api/auth/usuarios/`.
- **Resultado esperado:** la respuesta es **403** y el panel no muestra datos.

### CNF-02 · Carta en una pantalla de 360 × 640 px
**RNF2**

- **Pasos:**
  1. En Chrome, abrir las herramientas de desarrollo, activar el modo dispositivo con 360 × 640 y abrir la carta de la Mesa 1.
  2. Recorrer las categorías, agregar productos y abrir el carrito.
- **Resultado esperado:**
  - no hay desplazamiento horizontal;
  - los textos y botones se leen y se pueden tocar;
  - la barra del carrito no tapa el último producto.

### CNF-03 · Lighthouse en la carta
**RNF2** · Rendimiento obligatorio; accesibilidad como criterio complementario.

- **Pasos:** en Chrome, herramientas de desarrollo → Lighthouse → modo Móvil → analizar la carta de la Mesa 1. Repetir 3 veces.
- **Resultado esperado:**
  - la mediana de **Rendimiento es ≥ 80** y la de **Accesibilidad es ≥ 90**;
  - se anotan los tres puntajes de cada categoría y se adjunta el informe.

### CNF-04 · Tiempos de respuesta de la API
**RNF3** · Issue `#7`

- **Pasos:**
  1. Con el servidor de prueba en marcha, ejecutar desde `backend/` `python manage.py medir_tiempos --settings=config.settings_qa`.
  2. El script mide primero cada ruta con un solo usuario y luego con 10 usuarios simultáneos durante 60 s, sin pausas: 6 clientes que recorren la carta y piden, 2 de cocina y 2 garzones que entregan y cobran.
- **Resultado esperado:**
  - p95 < 1.500 ms en todas las rutas medidas;
  - carta (categorías y productos) y pedidos activos < 800 ms;
  - se adjunta el reporte con la media y el p95 por ruta.

### CNF-05 · Funcionamiento con datos de volumen
**RNF5**

- **Pasos:**
  1. Cargar en la base de prueba 20 mesas, 100 productos y 500 pedidos: `python manage.py cargar_datos_qa --settings=config.settings_qa --volumen`.
  2. Medir cuánto tardan en cargar la carta y la vista «Activos» de Pedidos.
  3. Repetir CNF-04.
- **Resultado esperado:** las pantallas cargan y los tiempos siguen dentro de los límites de CNF-04. Si no, se registra como defecto (relacionado con el issue `#16`).

### CNF-06 · Compatibilidad entre navegadores y dispositivos
**RNF6**

- **Pasos:** ejecutar los casos críticos en cada combinación disponible:
  - en móvil: CF-01, CF-03, CF-06 y CF-07;
  - en escritorio: CF-08, CF-20 y CF-25.
- **Resultado esperado:** cero errores funcionales en al menos 2 navegadores móviles y 2 de escritorio. La memoria declara solo los que se probaron.

| Navegador y versión | Dispositivo y sistema | Casos ejecutados | Resultado |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |

### CNF-07 · Caracteres especiales
**RNF7** · Se ejecuta con **MySQL**, en una base de prueba distinta de la real, porque comprueba la codificación `utf8mb4`.

- **Pasos:**
  1. Crear el producto `Ñoquis à la crème 🍝`.
  2. Enviar un pedido con la indicación `sin ají, ¡bien cocida!`.
- **Resultado esperado:** el nombre y la indicación se guardan y se muestran exactamente igual en la carta, en el panel de pedidos y en la cocina.

### CNF-08 · Mensajes ante errores, sin fallas del servidor
**Fiabilidad**

- **Pasos:** con la pestaña Red abierta, repetir las entradas inválidas de CF-04, CF-15 y CF-18.
- **Resultado esperado:** cada caso muestra un mensaje comprensible y ninguna respuesta de la API es **500**.

### CNF-09 · Revisión de mantenibilidad del repositorio
**RNF4**

- **Pasos:** revisar el repositorio en GitHub.
- **Resultado esperado:**
  - hay una app de Django por módulo (usuarios, productos, mesas, pedidos y pagos), cada una con modelos, serializers, vistas, rutas y pruebas;
  - las reglas de negocio no evidentes tienen un comentario: el orden de estados por rol, los avisos sin duplicar, la mesa con pedidos protegida, los topes de cantidad y el cobro que cierra el pedido;
  - el historial de commits usa mensajes con prefijo convencional.

### CNF-10 · Lectura del QR en distintos teléfonos
**Riesgo R06**

- **Pasos:** escanear el QR de la Mesa 1, impreso o en pantalla, a 30 cm y a 1 m, con al menos 2 teléfonos, de ser posible uno de gama media o baja.
- **Resultado esperado:** todos los teléfonos abren la carta de la Mesa 1. Se anotan los modelos usados.

---

## Cobertura de requerimientos

Cada requerimiento se verifica con pruebas automatizadas, con casos de este catálogo o con ambos.

| Requerimiento | Pruebas automatizadas | Casos del catálogo |
|---|---|---|
| RF01 | `usuarios` · LoginTests | CF-08, CF-09 |
| RF02 | `usuarios` · LoginTests | CF-08 |
| RF03 | `usuarios` · SesionTests | — (la renovación es automática e invisible) |
| RF04 | `usuarios` · SesionTests | CF-10 |
| RF05, RF06 | `usuarios` · GestionDeUsuariosTests | CF-12 |
| RF07 | `usuarios` · GestionDeUsuariosTests; `config` · MatrizDePermisosTests | CF-11, CF-19 |
| RF08 | `productos` · CategoriasTests | CF-13 |
| RF09, RF10 | `productos` · ProductosTests | CF-14, CF-15 |
| RF11 | `productos` · ProductosTests | CF-16 |
| RF12 | `mesas` · MesasTests | CF-17, CF-18 |
| RF13 | `mesas` · MesasTests | CF-01, CF-17 |
| RF14 | `mesas` · MesasTests | CF-19 |
| RF15, RF16 | `mesas` · MesasTests; `productos` · ProductosTests | CF-01, CF-03 |
| RF17 | — | CF-06 |
| RF18, RF19 | `pedidos` · NotaDetallePedidoTests, LimitesDeCantidadTests | CF-06 |
| RF20, RF21, RF22 | `pedidos` · HistorialYTransicionesTests | CF-20, CF-21 |
| RF23, RF24 | `config` · MatrizDePermisosTests (solo permisos) | CF-20, CF-23 |
| RF25, RF26, RF27 | `pagos` · PagosTests | CF-25 |
| RF28 | `pagos` · PagosTests | CF-28 |
| RF29 | — | CF-29 |
| RF30 | `pedidos` · NotaDetallePedidoTests | CF-03, CF-20 |
| RF31 | `pedidos` · HistorialYTransicionesTests | CF-20 |
| RF32 | — | CF-22 |
| RF33 | `mesas` · SolicitudesDeMesaTests | CF-07 |
| RF34 | `mesas` · SolicitudesDeMesaTests | CF-24 |
| RF35 | — | CF-20, CF-24 |
| RF36 | `pedidos` · LimitesDeCantidadTests | CF-04 |
| RF37 | — | CF-05 |
| RF38 | `mesas` · MesasTests | CF-01, CF-02 |
| RF39 | `pagos` · PagosTests | CF-26, CF-27 |
| RF40 | — | CF-29 |
| RF41 | `pedidos` · HistorialYTransicionesTests; `pagos` · PagosTests | CF-21 |
| RNF1 | `config` · MatrizDePermisosTests; `usuarios` · LoginTests | CF-10, CF-11, CNF-01 |
| RNF2 | — | CF-06, CNF-02, CNF-03 |
| RNF3 | — | CNF-04 |
| RNF4 | — | CNF-09 |
| RNF5 | — | CNF-05 |
| RNF6 | — | CNF-06 |
| RNF7 | `pagos` · PagosTests; `productos` · ProductosTests | CNF-07 |

## Observaciones conocidas al preparar el catálogo

| ID | Observación | Efecto |
|---|---|---|
| O1 | El formulario de usuarios exige una contraseña de al menos 8 caracteres; la API acepta 6 | Ninguno para el uso normal: el formulario es más estricto. Se documenta para que no se informe como defecto |
| — | Limitaciones L1 a L6 de la matriz de trazabilidad (rol o categoría inexistentes → 500 vía API, cobro de pedidos no entregados vía API, sin filtro por fecha, sin desglose por método, sin transacciones atómicas) | Conocidas y documentadas; no se informan como defectos |

## Registro de defectos

| ID | Fecha | Caso | Descripción | Pasos para repetirlo | Severidad | Estado | Issue o commit | Detectado por |
|---|---|---|---|---|---|---|---|---|
| D-01 | 2026-10-18 | CNF-04, CNF-05 | Con 500 pedidos y 10 usuarios simultáneos sin pausa, `GET /api/pedidos/` (vista «Activos») tarda 2.620 ms en el p95 (umbral: 800) y `GET /api/pagos/`, 4.087 ms (umbral: 1.500). Cada respuesta pesa más de 1 MB porque trae todo el historial. Al ritmo de la interfaz (un sondeo cada 10 s) cumple, con poco margen: 726 ms | CNF-05 con `cargar_datos_qa --volumen` y `medir_tiempos` | Media | Abierto | `#16` | Script `medir_tiempos` |
| D-02 | 2026-10-18 | CNF-04 | Si llegan al mismo tiempo dos peticiones para avanzar el mismo pedido, el servidor acepta las dos y el historial registra el paso dos veces | Enviar dos `PATCH /api/pedidos/<id>/estado/` simultáneos con el siguiente estado, por ejemplo con un doble toque en el botón de avanzar. Se repitió en 50 de 50 intentos | Baja | Abierto | — | Script `medir_tiempos` |
| D-03 | 2026-10-18 | CNF-04 | Si llegan al mismo tiempo dos cobros del mismo pedido, el servidor registra los dos: quedan dos pagos vigentes y la venta se cuenta dos veces. Contradice la regla de un solo pago vigente (RF25, RNF7) | Enviar dos `POST /api/pagos/` simultáneos para el mismo pedido entregado, por ejemplo desde dos dispositivos. Se repitió en 50 de 50 intentos | Alta | Abierto | — | Script `medir_tiempos` |

**Severidad:**
- **Crítica:** impide operar.
- **Alta:** afecta una función principal sin alternativa.
- **Media:** tiene alternativa.
- **Baja:** cosmética.

**Estados:** abierto → en corrección → verificado → cerrado.
