const query = `
[out:json][timeout:60];
area["name"="Cosquín"]["boundary"="administrative"][admin_level=8];
(
  way["building"](area);
  node["building"](area);
);
out center;
`;

(async () => {
  const res = await fetch("https://overpass-api.de/api/interpreter", {
    method: "POST",
    body: query,
  });

  const data = await res.json();

  const filas = data.elements.map(el => {
    let lat = el.lat;
    let lon = el.lon;
    if (el.type === 'way' && el.center) {
      lat = el.center.lat;
      lon = el.center.lon;
    }
    const direccion = `OSM-${el.id}`;
    return `('${direccion}', ${lat}, ${lon})`;
  });

  const sql = `INSERT INTO casas (direccion, latitud, longitud) VALUES\n${filas.join(',\n')};`;

  console.log(sql);
})();
