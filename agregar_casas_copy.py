import requests
import geopandas as gpd
from io import BytesIO

# --- 1. Definición de la zona delimitada (Bounding Box) ---

min_lat_d = -31.259917  # Esquina inferior
max_lat_d = -31.243621  # Esquina superior
min_lon_d = -64.462306  # Esquina izquierda
max_lon_d = -64.433140  # Esquina derecha

# Formato del BBOX para WFS: minLon,minLat,maxLon,maxLat,CRS
bbox_coords = f"{min_lon_d},{min_lat_d},{max_lon_d},{max_lat_d}"
crs_code = "EPSG:4326"  # Sistema de Coordenadas de Referencia

# --- 2. Configuración del servicio WFS de IDECOR ---
wfs_url = "https://idecor-ws.mapascordoba.gob.ar/geoserver/idecor/wfs"
layer_name = "idecor:parcelas"  # Verificá este nombre con QGIS si da vacío

# --- 3. Parámetros para la solicitud WFS ---
params = {
    'service': 'WFS',
    'version': '1.0.0',
    'request': 'GetFeature',
    'typeName': layer_name,
    'outputFormat': 'application/json',
    'srsName': crs_code,
    'bbox': f"{bbox_coords},{crs_code}"
}

print(f"Solicitando datos a IDECOR para la capa '{layer_name}'...")

try:
    response = requests.get(wfs_url, params=params)
    response.raise_for_status()

    content_type = response.headers.get('content-type', '').split(';')[0].strip()
    if content_type == 'application/json':
        geojson_data = response.json()
        if not geojson_data.get('features'):
            print("No se encontraron parcelas en el área definida.")
            exit()

        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        gdf.set_crs(crs_code, allow_override=True, inplace=True)
    else:
        print(f"Respuesta inesperada. Tipo de contenido: {content_type}")
        exit()

    # Procesamiento de geometrías
    gdf = gdf[gdf.geometry.notnull()]
    gdf['centroid'] = gdf.geometry.centroid
    gdf = gdf[gdf['centroid'].is_valid]
    gdf['latitud'] = gdf['centroid'].y
    gdf['longitud'] = gdf['centroid'].x

    # --- Generar SQL ---
    filas_sql = []
    current_id = 0

    for _, row in gdf.iterrows():
        direccion = str(row.get('nomenclatura') or row.get('gid') or f"IDECOR_Parcela_{current_id}")
        direccion_escaped = direccion.replace("'", "''")
        lat = row['latitud']
        lon = row['longitud']
        filas_sql.append(f"({current_id}, '{direccion_escaped}', {lat}, {lon})")
        current_id += 1

    if filas_sql:
        filas_unidas = ',\n'.join(filas_sql)
        sql_insert = f"""INSERT INTO casas (id, direccion, latitud, longitud) VALUES
{filas_unidas};"""
        print("\n--- SQL Generado ---")
        print(sql_insert)
    else:
        print("No se generaron filas SQL.")

except requests.exceptions.RequestException as e:
    print(f"Error de conexión o servicio WFS: {e}")
except Exception as e:
    print(f"Error inesperado: {e}")
