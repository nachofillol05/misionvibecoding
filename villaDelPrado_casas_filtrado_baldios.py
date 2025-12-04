import requests
import geopandas as gpd
from io import BytesIO

# --- Función para convertir DMS a Decimal ---
def dms_to_decimal(degrees, minutes, seconds, direction):
    decimal = float(degrees) + float(minutes)/60 + float(seconds)/3600
    if direction in ['S', 'W']:
        decimal *= -1
    return decimal

# --- BBOX en DMS convertidos ---
min_lat_d = dms_to_decimal(31, 37, 48.4, 'S')
max_lat_d = dms_to_decimal(31, 36, 17.1, 'S')
min_lon_d = dms_to_decimal(64, 25, 6.0, 'W')
max_lon_d = dms_to_decimal(64, 22, 4.0, 'W')

bbox_coords = f"{min_lon_d},{min_lat_d},{max_lon_d},{max_lat_d}"
crs_code = "EPSG:4326"

# --- Configuración del WFS ---
wfs_url = "https://idecor-ws.mapascordoba.gob.ar/geoserver/idecor/wfs"
layer_name = "idecor:parcelas"

params = {
    'service': 'WFS',
    'version': '1.0.0',
    'request': 'GetFeature',
    'typeName': layer_name,
    'outputFormat': 'application/json',
    'srsName': crs_code,
    'bbox': f"{bbox_coords},{crs_code}"
}

print("Descargando parcelas dentro del BBOX...")
resp = requests.get(wfs_url, params=params)
resp.raise_for_status()

gjson = resp.json()
gdf = gpd.GeoDataFrame.from_features(gjson["features"])
gdf.set_crs(crs_code, allow_override=True, inplace=True)

# --- Calcular centroides ---
gdf["centroid"] = gdf.geometry.centroid
gdf["latitud"] = gdf["centroid"].y
gdf["longitud"] = gdf["centroid"].x

# --- Normalizamos el campo Estado ---
gdf["Estado"] = gdf["Estado"].astype(str).str.upper()

gdf_baldios = gdf[gdf["Estado"].str.contains("BALD")]
gdf_edificados = gdf[gdf["Estado"].str.contains("EDIF")]

print(f"Total parcelas descargadas: {len(gdf)}")
print(f"Encontrados EDIFICADOS: {len(gdf_edificados)}")
print(f"Encontrados BALDIOS: {len(gdf_baldios)}")

# --- Función para crear SQL ---
def generar_sql(nombre_archivo, gdf):
    filas = []
    current_id = 0

    for _, row in gdf.iterrows():
        direccion = str(row.get("nomenclatura", f"Parcela_{current_id}"))
        direccion = direccion.replace("'", "''")

        lat = row["latitud"]
        lon = row["longitud"]

        filas.append(f"({current_id}, '{direccion}', {lat}, {lon})")
        current_id += 1

    sql = f"INSERT INTO public.casas (id, direccion, latitud, longitud) VALUES\n" + ",\n".join(filas) + ";"

    with open(nombre_archivo, "w") as f:
        f.write(sql)

    print(f"Archivo generado: {nombre_archivo} ({len(filas)} filas)")


# --- Generar archivos SQL ---
generar_sql("casas_edificadas.sql", gdf_edificados)
"""generar_sql("casas_baldios.sql", gdf_baldios)"""
