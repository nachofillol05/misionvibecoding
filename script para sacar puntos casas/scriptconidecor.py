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

# --- 1. Definición de la zona delimitada (Bounding Box) en Cosquín ---
# Tus coordenadas de la zona delimitada en formato DMS
# Izquierda inferior: 31°14'34.1"S 64°28'03.4"W
# Derecha inferior: 31°14'41.4"S 64°27'25.4"W
# Superior izquierda: 31°13'59.1"S 64°27'55.0"W
# Superior derecha: 31°14'02.2"S 64°27'11.5"W

# Convertir DMS a grados decimales
# Longitud mínima (más al oeste)
min_lon_d = dms_to_decimal(64, 28, 3.4, 'W')
# Latitud mínima (más al sur)
min_lat_d = dms_to_decimal(31, 14, 41.4, 'S') # Usamos la de la esquina inferior derecha, que es más al sur

# Longitud máxima (más al este)
max_lon_d = dms_to_decimal(64, 27, 11.5, 'W')
# Latitud máxima (más al norte)
max_lat_d = dms_to_decimal(31, 13, 59.1, 'S')

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
    # La línea gdf.to_crs(crs_code) ya no es estrictamente necesaria aquí si set_crs fue exitoso,
    # pero la dejamos por si acaso o para reproyectar a otro CRS en el futuro.
    # En este caso, no hace daño si ya está seteado.
    if gdf.crs != crs_code:
        gdf = gdf.to_crs(crs_code)

    # Calcular el centroide de cada geometría (parcela/casa)
    # Algunas geometrías pueden ser nulas o inválidas, las filtramos
    gdf['centroid'] = gdf.geometry.centroid
    gdf = gdf[gdf['centroid'].is_valid]

    # Extraer latitud y longitud
    gdf['latitud'] = gdf['centroid'].y
    gdf['longitud'] = gdf['centroid'].x

    # --- 6. Formatear la salida SQL ---
    filas_sql = []
    for index, row in gdf.iterrows():
        # Aquí puedes elegir qué propiedad de la parcela usar como 'direccion'.
        # Es muy recomendable usar un campo de IDECOR si existe, como 'NomenclaturaCatastral', 'id_parcela', etc.
        # Puedes descomentar la siguiente línea para ver los nombres de las columnas/atributos disponibles
        # print(row.keys())

        # Por defecto, intentamos usar 'nomenclatura' si existe, o 'gid', o un identificador generado
        direccion = ""
        if 'nomenclatura' in row and row['nomenclatura']:
            direccion = str(row['nomenclatura'])
        elif 'gid' in row and row['gid']:
            direccion = str(row['gid'])
        else:
            direccion = f"IDECOR_Parcela_{index}" # Genera un ID si no hay uno más descriptivo

        lat = row['latitud']
        lon = row['longitud']

        # Escapar comillas simples en la dirección para SQL (doblando la comilla)
        direccion_escaped = str(direccion).replace("'", "''")

        filas_sql.append(f"('{direccion_escaped}', {lat}, {lon})")

    if filas_sql:
        # Generar la parte de las filas del SQL por separado
        filas_unidas = ',\n'.join(filas_sql)

        # Ahora construir el SQL completo usando un f-string multilinea
        sql_insert = f"""INSERT INTO casas (direccion, latitud, longitud) VALUES
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