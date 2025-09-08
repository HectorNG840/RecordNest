![Imagotipo](https://iili.io/KomU2Jn.md.png)

Aplicación web en Django para organizar colecciones de discos, integrando la API de [Discogs](https://www.discogs.com) y la API de [Deezer](https://www.deezer.com) para previews.

## Índice
- [Descripción](#descripción)
- [Funciones](#funciones)
- [Tecnologías](#tecnologías)
- [Dependencias principales](#dependencias-principales)
- [Instalación](#instalación)
- [Configuración de credenciales](#configuración-de-credenciales)
- [Uso](#uso)
- [Problemas y sugerencias](#problemas-y-sugerencias)

## Descripción
RecordNest permite a los usuarios gestionar su colección de discos, buscar información a través de Discogs, escuchar fragmentos gracias a Deezer, recibir recomendaciones mediante un recomendador semántico, crear listas y visitar perfiles de otras personas.

## Funciones
- Añadir, editar y borrar discos.
- Búsqueda avanzada con Discogs.
- Previsualizaciones de audio desde Deezer.
- Crear listas.
- Obtener recomendaciones mediante un recomendador semántico.
- Añadir discos a lista de deseos.
- Ver estadisticas personales y estadisticas generales de la aplicación.

## Tecnologías
- Django (5.1.5), Python 3.12.6  
- HTML5, CSS3 
- Discogs API, Deezer API  
- SQLite

## Dependencias principales
- Django==5.1.5 — Framework web principal.
- pytest-django — Testing.
- Pillow — Manejo de imágenes.
- discog-client — Cliente para la API de Discogs.
- python-decouple — Gestión de variables de entorno y configuración.
- bbcode — Renderizado de BBCode.
- scikit-learn — Algoritmos de machine learning.
- sentence-transformers — Modelos semánticos para el recomendador.

## Instalación
1. Clona este repositorio:
   ```bash
   git clone https://github.com/HectorNG840/RecordNest.git
   cd RecordNest
   ```
2. Crea y activa un entorno virtual con Python 3.12.6:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate   # En Linux / Mac
   venv\Scripts\activate      # En Windows
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Realiza y aplica las migraciones:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Ejecuta el servidor de desarrollo
   ```bash
   python manage.py runserver
   ```   

## Configuración de credenciales

### 1) Crear tu archivo `.env`
Copia el archivo de ejemplo y rellena los valores:

**Linux/Mac**
```bash
cp .env.example .env
```
**Windows**
```bash
Copy-Item .env.example .env
```
No subas .env al repositorio. Mantén tus credenciales en local.

### 2) Claves de Discogs (consumer key/secret)

#### 1. Ve a Discogs Developers y crea una [aplicación](https://www.discogs.com/settings/developers) (sección Developers de tu cuenta).
#### 2. Configura el Callback URL exactamente igual que en tu .env (por defecto):
```bash
DISCOGS_CALLBACK_URL=http://127.0.0.1:8000/discogs/callback/
```
#### 3. Copia tu Consumer Key y Consumer Secret en el .env:
```bash
DISCOGS_CONSUMER_KEY=tu_consumer_key
DISCOGS_CONSUMER_SECRET=tu_consumer_secret
```
### 3) Obtener Access Token/Secret de Discogs (OAuth)

Con el entorno virtual activo y desde la raíz del proyecto (donde está manage.py), ejecuta el script:
```bash
python -m records.get_discogs_oauth_token
```
El script te mostrará una URL de autorización.

#### 1. Ábrela en el navegador y autoriza la app.
#### 2. Copia el oauth_verifier que te da Discogs y pégalo en la consola cuando te lo pida.
#### 3. El script imprimirá tu ACCESS TOKEN y ACCESS SECRET. Ponlos en tu .env:
```bash
DISCOGS_OAUTH_TOKEN=tu_access_token
DISCOGS_OAUTH_SECRET=tu_access_secret
```

### 4) Email (Gmail)
Para enviar correos con Gmail:
```bash
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password_de_gmail
DEFAULT_FROM_EMAIL="RecordNest <tu_correo@gmail.com>"
```
Recomendado: usar un App Password de Google.

### 5) Reinicia el servidor
Después de actualizar el .env, reinicia el servidor de desarrollo:
```bash
python manage.py runserver
```

## Uso

Aqui se muestran unas capturas de pantalla donde se ve el uso básico de la aplicación.

1. Creación de usuario  

   ![Creación de usuario](https://iili.io/KoG9IeV.png)

2. Búsqueda de discos 

   ![Busqueda de discos](https://iili.io/KoGqVTJ.png)
   
4. Detalles disco

   ![Deatlles disco](https://iili.io/KoGxEzu.png)

5. Colección

  ![Colección](https://iili.io/KoDUFHb.png)

6. Lista de deseos

 ![Wishlist](https://iili.io/KoD6eTb.png)
 
7. Listas personales

  ![Listas](https://iili.io/KoDpTrJ.png)

8. Estadisticas generales  

  ![Estadísticas generales](https://iili.io/KoGA0Vn.jpg)

9. Top discos 

  ![Top Discos](https://iili.io/KoDlc3F.jpg)

10. Perfil
   
  ![Perfil](https://iili.io/KoDMMqQ.png)

11. Apartado Social

  ![Social](https://iili.io/KobuFbS.png)

## Problemas y sugerencias

Si encuentras algún problema, bug o tienes alguna sugerencia de mejora, por favor abre un [issue](https://github.com/HectorNG840/RecordNest/issues) en este repositorio.  


