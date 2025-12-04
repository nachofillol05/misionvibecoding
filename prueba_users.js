import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 50 },
    { duration: '30s', target: 100 },
    { duration: '30s', target: 200 },
    { duration: '10s', target: 0 },
  ],
};


export default function () {
  // Cambiá esta URL por la de tu app en Render:
  http.get('https://misionvibecoding.onrender.com/');
  sleep(1);
}
