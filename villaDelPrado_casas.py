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
min_lat_d = dms_to_decimal(31, 37, 48.4, 'S')  # ≈ -31.630111

# Latitud máxima (más al norte)
max_lat_d = dms_to_decimal(31, 36, 17.1, 'S')  # ≈ -31.604750

# Longitud mínima (más al oeste)
min_lon_d = dms_to_decimal(64, 25, 6.0, 'W')   # ≈ -64.418333

# Longitud máxima (más al este)
max_lon_d = dms_to_decimal(64, 22, 4.0, 'W')   # ≈ -64.367778


# Formato del BBOX para WFS: minLon,minLat,maxLon,maxLat,CRS
bbox_coords = f"{min_lon_d},{min_lat_d},{max_lon_d},{max_lat_d}"
crs_code = "EPSG:4326" # Sistema de Coordenadas de Referencia (WGS84 para lat/lon)

# --- 2. Configuración del servicio WFS de IDECOR ---
wfs_url = "https://idecor-ws.mapascordoba.gob.ar/geoserver/idecor/wfs"

# Nombre de la capa de IDECOR que contiene las parcelas/casas.
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

    content_type = response.headers.get('content-type', '').split(';')[0].strip()
    if content_type == 'application/json':
        geojson_data = response.json()
        if not geojson_data or not geojson_data.get('features'):
            print("No se encontraron elementos (parcelas/casas) en la zona delimitada o la capa no tiene datos.")
            print("Por favor, verifica el 'layer_name' y las coordenadas del 'bbox'.")
            exit()

        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        gdf.set_crs(crs_code, allow_override=True, inplace=True)
    else:
        print(f"Error: El servicio WFS no devolvió 'application/json'. Tipo de contenido recibido: {content_type}")
        exit()

    if gdf.crs != crs_code:
        gdf = gdf.to_crs(crs_code)

    gdf['centroid'] = gdf.geometry.centroid
    gdf = gdf[gdf['centroid'].is_valid]
    gdf['latitud'] = gdf['centroid'].y
    gdf['longitud'] = gdf['centroid'].x

    filas_sql = []
    current_id = 0 

    for index, row in gdf.iterrows():
        direccion = ""
        if 'nomenclatura' in row and row['nomenclatura']:
            direccion = str(row['nomenclatura'])
        elif 'gid' in row and row['gid']:
            direccion = str(row['gid'])
        else:
            direccion = f"IDECOR_Parcela_{current_id}" 

        lat = row['latitud']
        lon = row['longitud']
        direccion_escaped = str(direccion).replace("'", "''")

        filas_sql.append(f"({current_id}, '{direccion_escaped}', {lat}, {lon})")
        current_id += 1

    if filas_sql:
        filas_unidas = ',\n'.join(filas_sql)
        sql_insert = f"""INSERT INTO public.casas (id, direccion, latitud, longitud) VALUES
{filas_unidas};"""

        print("\n--- SQL Generado ---")
        print(sql_insert)
    else:
        print("No se generaron filas SQL. Posiblemente no se encontraron parcelas en la zona.")

except requests.exceptions.RequestException as e:
    print(f"Error al conectar o recibir datos del servicio WFS de IDECOR: {e}")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")
