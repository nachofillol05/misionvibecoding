const express = require('express');
const http = require('http');
const cors = require('cors');
const { Server } = require('socket.io');
const pool = require('./db');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Obtener casas de usuario (solo las asignadas)
app.get('/casas/:usuario', async (req, res) => {
  const { usuario } = req.params;
  const resultado = await pool.query(
    'SELECT * FROM casas WHERE asignado_a = $1',
    [usuario]
  );
  res.json(resultado.rows);
});

// Obtener todas las casas (admin)
app.get('/casas', async (req, res) => {
  const resultado = await pool.query('SELECT * FROM casas');
  res.json(resultado.rows);
});

// Cambiar estado
app.post('/estado', async (req, res) => {
  const { id, estado } = req.body;
  await pool.query('UPDATE casas SET estado = $1 WHERE id = $2', [estado, id]);
  io.emit('actualizacion');
  res.sendStatus(200);
});

// Guardar comentario
app.post('/comentario', async (req, res) => {
  const { id, comentario } = req.body;
  await pool.query('UPDATE casas SET comentario = $1 WHERE id = $2', [comentario, id]);
  io.emit('actualizacion');
  res.sendStatus(200);
});

// Asignar casas (admin)
app.post('/asignar', async (req, res) => {
  const { ids, usuario } = req.body;
  await pool.query(
    'UPDATE casas SET asignado_a = $1 WHERE id = ANY($2::int[])',
    [usuario, ids]
  );
  io.emit('actualizacion');
  res.sendStatus(200);
});

// Desasignar casa (usuario)
app.post('/desasignar', async (req, res) => {
  const { id } = req.body;
  await pool.query('UPDATE casas SET asignado_a = NULL, estado = NULL, comentario = NULL WHERE id = $1', [id]);
  io.emit('actualizacion');
  res.sendStatus(200);
});
