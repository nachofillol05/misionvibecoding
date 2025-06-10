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

// Obtener casas asignadas a un usuario
app.get('/casas/:usuario', async (req, res) => {
  const usuario = req.params.usuario;
  try {
    const result = await pool.query('SELECT * FROM casas WHERE asignado_a = $1 ORDER BY id', [usuario]);
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error en la consulta');
  }
});

// Obtener todas las casas (para admin)
app.get('/casas', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM casas ORDER BY id');
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error en la consulta');
  }
});

// Asignar casas a un usuario (admin)
app.post('/asignar', async (req, res) => {
  const { casaIds, usuario } = req.body;
  try {
    await pool.query(
      `UPDATE casas SET asignado_a = $1 WHERE id = ANY($2::int[])`,
      [usuario, casaIds]
    );
    io.emit('actualizacion'); // Avisar a todos los clientes que hubo cambio
    res.sendStatus(200);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error al asignar casas');
  }
});

// Actualizar estado de una casa (visitada, no atendieron, otro)
// Reemplazá la ruta /estado actual con esta versión:
app.post('/estado', async (req, res) => {
  const { id, estado, comentario, usuario } = req.body;
  try {
    await pool.query(
      `UPDATE casas SET estado = $1, comentario = $2, actualizado_por = $3, updated_at = NOW() WHERE id = $4`,
      [estado, comentario, usuario, id]
    );
    io.emit('actualizacion');
    res.sendStatus(200);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error al actualizar estado');
  }
});



// WebSockets para updates en tiempo real
io.on('connection', (socket) => {
  console.log('Cliente conectado');
});

// Iniciar servidor
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Servidor escuchando en puerto ${PORT}`);
});
