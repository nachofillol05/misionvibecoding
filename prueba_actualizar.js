import http from 'k6/http';
import { check, sleep } from 'k6';

// 🔧 CONFIGURACIÓN DE CARGA
export const options = {
  stages: [
    { duration: '10s', target: 10 },   // Suben a 10 usuarios
    { duration: '20s', target: 30 },   // Mantiene 30 usuarios
    { duration: '20s', target: 60 },   // Sube a 60 usuarios
    { duration: '10s', target: 0 },    // Baja
  ],
};

// 🧠 DATOS DE PRUEBA
const ids = [
  "IDECOR_Parcela_7286",
  "IDECOR_Parcela_7287",
  "IDECOR_Parcela_7288",
  "IDECOR_Parcela_7289",
  "IDECOR_Parcela_7290",
];

export default function () {
  const url = 'https://misionvibecoding.onrender.com/actualizar'; // 👈 CAMBIÁ esto por tu URL real en Render

  const id = ids[Math.floor(Math.random() * ids.length)];
  const payload = JSON.stringify({
    id: id,
    estado: 'visitada',
    comentario: ''
  });

  const headers = { 'Content-Type': 'application/json' };

  const res = http.post(url, payload, { headers });

  // Validamos respuesta
  check(res, {
    'status 200': (r) => r.status === 200,
    'tiempo < 1s': (r) => r.timings.duration < 1000
  });

  sleep(1);
}
