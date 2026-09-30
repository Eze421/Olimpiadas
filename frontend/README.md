# Frontend

Interfaz base en HTML, CSS y JavaScript sin framework. Incluye catálogo público adaptable a celular y una vista de administración conectada a la API.

## Ejecutar en desarrollo

1. Iniciá el backend según las instrucciones de `../backend/README.md`.
2. En otra terminal, desde esta carpeta ejecutá:

   ```bash
   python3 -m http.server 5500
   ```

3. Abrí <http://127.0.0.1:5500>.

La URL de la API por defecto es `http://127.0.0.1:8000` en desarrollo local. Si necesitás otro puerto local, podés agregar `?api=http://localhost:PUERTO`; por seguridad, el frontend solo acepta overrides locales o de su propio origen. El backend permite CORS para `localhost:5500` y `127.0.0.1:5500` en desarrollo local.

La gestión de productos requiere iniciar sesión con una cuenta de Jefe de ventas. Los clientes pueden crear una cuenta desde Ingresar/Carrito; el registro los inicia automáticamente. Las imágenes se envían al backend y se leen desde su ruta `/media/`.

El carrito requiere una cuenta de cliente y se almacena en el backend por 15 minutos desde su creación. La interfaz permite agregar productos, modificar cantidades, quitar líneas y vaciarlo. Todavía no hay checkout ni procesamiento de pagos.
