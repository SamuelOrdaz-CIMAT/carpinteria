# Programa de carpinteria

Aplicacion local para manejar materiales, proveedores, precios, tipos de muebles y presupuestos.

## Como abrirlo

```powershell
python app.py
```

Despues entra en el navegador a:

```text
http://127.0.0.1:5000
```

## Como verlo desde el celular

1. Asegurate de que la computadora y el celular esten conectados al mismo Wi-Fi.
2. Cierra el servidor anterior si sigue abierto.
3. Vuelve a iniciar la app:

```powershell
python app.py
```

4. En el celular abre:

```text
http://192.168.1.110:5000
```

Si Windows pregunta por permisos de red para Python, permite el acceso en redes privadas.

## Como compartirlo fuera de tu red

Para compartirlo con alguien fuera de tu casa, usa un tunel temporal como Cloudflare Tunnel o ngrok. Antes de abrirlo a internet, pon una contrasena:

```powershell
$env:CARPINTERIA_PASSWORD="pon-una-contrasena"
python app.py
```

Con eso la app pedira contrasena al abrir el enlace publico.

## Opcion gratis sin tener tu computadora prendida

La opcion gratis mas sencilla es PythonAnywhere.

### Archivos incluidos

```text
requirements.txt        # paquetes necesarios
pythonanywhere_wsgi.py  # ejemplo de configuracion WSGI
```

### Pasos generales

1. Crea una cuenta gratis en `https://www.pythonanywhere.com`.
2. Sube esta carpeta como `Carpinteria` a tu cuenta.
3. Abre una consola Bash en PythonAnywhere.
4. Instala dependencias:

```bash
cd ~/Carpinteria
pip3 install --user -r requirements.txt
```

5. En la pestana `Web`, crea una nueva app Flask/manual.
6. En el archivo WSGI de PythonAnywhere, copia el contenido de `pythonanywhere_wsgi.py`.
7. Cambia la contrasena:

```python
os.environ.setdefault("CARPINTERIA_PASSWORD", "tu-contrasena-real")
```

8. Asegurate de subir tambien `carpinteria.db`.
9. Presiona `Reload` en la pestana `Web`.

Tu app quedara en una URL parecida a:

```text
https://tuusuario.pythonanywhere.com
```

## Actualizar con GitHub

Repositorio:

```text
https://github.com/SamuelOrdaz-CIMAT/carpinteria
```

En tu computadora:

```powershell
git add .
git commit -m "Describe el cambio"
git push
```

En PythonAnywhere:

```bash
cd ~/Carpinteria
git pull
```

Luego entra a la pestana `Web` y presiona `Reload`.

No subas `carpinteria.db` al repo. Esa base se queda viva en PythonAnywhere.

La primera vez importa los materiales y precios desde `Precios_Julio_2026.xlsx` y crea la base `carpinteria.db`.

## Flujo de uso

1. Entra a `Configuracion` y captura datos del taller, WhatsApp, vigencia y condiciones de pago.
2. Actualiza proveedores y materiales; puedes editar varias filas, usar `Guardar cambios` o eliminar registros que ya no ocupes.
3. Captura precios en la matriz de precios.
4. Crea un tipo de mueble.
5. Entra a `Materiales y presupuesto` para capturar que materiales necesita, cantidades, merma y proveedor sugerido.
6. Genera un presupuesto con cliente, cantidad, mano de obra y margen.
7. Abre el presupuesto guardado para modificarlo, eliminarlo, descargar la cotizacion PDF final o usar el boton de WhatsApp.
8. El margen de ganancia se calcula solo sobre materiales; la mano de obra se suma aparte.

## Respaldos

En `Configuracion` usa `Descargar respaldo` para guardar una copia de `carpinteria.db`.

## Estructura del proyecto

```text
app.py                  # arranque de la app
carpinteria/database.py # base de datos, schema e importacion inicial
carpinteria/routes/     # pantallas y acciones por seccion
carpinteria/services/   # calculos, PDF, precios, presupuestos
carpinteria/utils.py    # utilidades compartidas
templates/              # HTML
static/                 # estilos
```
