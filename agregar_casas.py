import requests
import geopandas as gpd
from io import BytesIO

# --- Función para convertir Grados, Minutos, Segundos (DMS) a Grados Decimales ---
def dms_to_decimal(degrees, minutes, seconds, direction):
    """Convierte coordenadas DMS a grados decimales."""
    decimal = float(degrees) + float(minutes)/60 + float(seconds)/(3600)
    if direction in ['S', 'W']:
        decimal *= -1
    return decimal

# --- 1. Definición de la zona delimitada (Bounding Box) ---
# Tus nuevas coordenadas de la zona delimitada en formato DMS
# sup der: 31°36'26.0"S 64°22'04.0"W
# inf der: 31°37'48.4"S 64°22'07.2"W
# inf izqu: 31°37'43.5"S 64°25'06.0"W
# sup izq: 31°36'17.1"S 64°24'46.9"W

# Convertir DMS a grados decimales para el nuevo BBOX
# Latitud mínima (más al sur)
# Latitud mínima (más al sur) → desde 31°15'35.7"S
min_lat_d = dms_to_decimal(31, 15, 35.7, 'S')  # ≈ -31.259917

# Latitud máxima (más al norte) → desde -31.243621 (ya decimal)
max_lat_d = -31.243621

# Longitud mínima (más al oeste) → desde 64°27'44.3"W
min_lon_d = dms_to_decimal(64, 27, 44.3, 'W')  # ≈ -64.462306

# Longitud máxima (más al este) → desde 64°26'06.6"W
max_lon_d = dms_to_decimal(64, 26, 6.6, 'W')   # ≈ -64.435167


# Formato del BBOX para WFS: minLon,minLat,maxLon,maxLat,CRS
bbox_coords = f"{min_lon_d},{min_lat_d},{max_lon_d},{max_lat_d}"
crs_code = "EPSG:4326" # Sistema de Coordenadas de Referencia (WGS84 para lat/lon)

# --- 2. Configuración del servicio WFS de IDECOR ---
wfs_url = "https://idecor-ws.mapascordoba.gob.ar/geoserver/idecor/wfs"

# Nombre de la capa de IDECOR que contiene las parcelas/casas.
# ¡IMPORTANTE: DEBES CONFIRMAR ESTE NOMBRE CON QGIS O LA DOCUMENTACIÓN DE IDECOR!
# Si este nombre no es exacto, el script no encontrará datos.
layer_name = "idecor:parcelas" # <<<<<<< ¡VERIFICÁ Y CAMBIÁ ESTO SI ES NECESARIO!

# --- 3. Parámetros para la solicitud WFS GetFeature ---
params = {
    'service': 'WFS',
    'version': '1.0.0', # La versión común. Podría ser '2.0.0' en algunos casos.
    'request': 'GetFeature',
    'typeName': layer_name,
    'outputFormat': 'application/json', # Pedimos GeoJSON
    'srsName': crs_code, # Especificamos el CRS para la salida
    'bbox': f"{bbox_coords},{crs_code}" # Aplicamos el filtro de la zona
}

# --- 4. Realizar la solicitud al WFS ---
print(f"Intentando obtener datos de la capa '{layer_name}' de IDECOR...")
print(f"URL de la solicitud (para depuración): {wfs_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}")

try:
    response = requests.get(wfs_url, params=params)
    response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)

    # Verificar si la respuesta es GeoJSON
    content_type = response.headers.get('content-type', '').split(';')[0].strip()
    if content_type == 'application/json':
        geojson_data = response.json()
        if not geojson_data or not geojson_data.get('features'):
            print("No se encontraron elementos (parcelas/casas) en la zona delimitada o la capa no tiene datos.")
            print("Por favor, verifica el 'layer_name' y las coordenadas del 'bbox'.")
            exit()

        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        
        # --- SOLUCIÓN AL ERROR DE GEOMETRÍAS NAIVE ---
        # Forzamos el CRS de la GeoDataFrame. Asumimos que los datos ya vienen en EPSG:4326.
        gdf.set_crs(crs_code, allow_override=True, inplace=True)
        # -----------------------------------------------

    else:
        print(f"Error: El servicio WFS no devolvió 'application/json'. Tipo de contenido recibido: {content_type}")
        print("Esto puede significar que el 'outputFormat' no es soportado o la solicitud es incorrecta.")
        print("Intenta revisar la documentación de IDECOR o usar QGIS para depurar la conexión WFS.")
        exit()

    # --- 5. Procesar los datos y generar los centroides ---
    if gdf.crs != crs_code:
        gdf = gdf.to_crs(crs_code)

    # Calcular el centroide de cada geometría (parcela/casa)
    # Algunas geometrías pueden ser nulas o inválidas, las filtramos
    gdf['centroid'] = gdf.geometry.centroid
    gdf = gdf[gdf['centroid'].is_valid]

    # Extraer latitud y longitud
    gdf['latitud'] = gdf['centroid'].y
    gdf['longitud'] = gdf['centroid'].x

    # --- 6. Formatear la salida SQL con ID inicial en 2500 ---
    filas_sql = []
    # Inicializa el contador de ID
    current_id = 0 

    for index, row in gdf.iterrows():
        # Puedes seguir usando 'nomenclatura' o 'gid' si quieres una 'dirección' más descriptiva
        # Si prefieres que el ID numérico sea la "dirección", simplemente usa current_id.
        direccion = ""
        if 'nomenclatura' in row and row['nomenclatura']:
            direccion = str(row['nomenclatura'])
        elif 'gid' in row and row['gid']:
            direccion = str(row['gid'])
        else:
            # Si no hay nomenclatura ni gid, usa un ID basado en el contador
            direccion = f"IDECOR_Parcela_{current_id}" 

        lat = row['latitud']
        lon = row['longitud']

        # Escapar comillas simples en la dirección para SQL (doblando la comilla)
        direccion_escaped = str(direccion).replace("'", "''")

        # **Aquí está el cambio clave:** Agregamos el `current_id` a la inserción
        filas_sql.append(f"({current_id}, '{direccion_escaped}', {lat}, {lon})")
        
        # Incrementa el ID para la siguiente fila
        current_id += 1

    if filas_sql:
        # Generar la parte de las filas del SQL por separado
        filas_unidas = ',\n'.join(filas_sql)

        # **Modificación en el INSERT INTO para incluir el nuevo campo 'id'**
        # Asume que tu tabla `casas` tiene una columna `id` (por ejemplo, INT PRIMARY KEY)
        sql_insert = f"""INSERT INTO casas (id, direccion, latitud, longitud) VALUES
{filas_unidas};"""

        print("\n--- SQL Generado ---")
        print(sql_insert)
    else:
        print("No se generaron filas SQL. Posiblemente no se encontraron parcelas en la zona.")

except requests.exceptions.RequestException as e:
    print(f"Error al conectar o recibir datos del servicio WFS de IDECOR: {e}")
    print("Por favor, verifica tu conexión a internet, la URL del WFS, y si el servicio está activo.")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")
