async function generarSQLInsertCasas(zona = "Cosquín, Córdoba", cantidad = 600) {
  const geoResp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(zona)}`);
  const geoData = await geoResp.json();
  if (!geoData.length) {
    console.error("Zona no encontrada");
    return;
  }

  const { lat, lon } = geoData[0];
  const casas = [];

  for (let i = 0; i < cantidad; i++) {
    const latOffset = (Math.random() - 0.5) * 0.005;
    const lonOffset = (Math.random() - 0.5) * 0.005;
    const nuevaLat = (parseFloat(lat) + latOffset).toFixed(6);
    const nuevaLon = (parseFloat(lon) + lonOffset).toFixed(6);
    casas.push(`('Casa ${i + 1}', ${nuevaLat}, ${nuevaLon})`);
  }

  const sql = `INSERT INTO casas (direccion, latitud, longitud) VALUES\n${casas.join(",\n")};`;
  console.log(sql);
  return sql;
}

// Usalo así:
generarSQLInsertCasas();
