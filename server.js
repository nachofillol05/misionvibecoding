const express = require('express');
const http = require('http');
const cors = require('cors');
const { Server } = require('socket.io');
const pool = require('./db');  // Tu pool de conexión a BD

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Rutas aquí
app.get('/casas/:usuario', async (req, res) => {
  const { usuario } = req.params;
  try {
    const resultado = await pool.query(
      'SELECT * FROM casas WHERE asignado_a = $1',
      [usuario]
    );
    res.json(resultado.rows);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error en la consulta');
  }
});

app.get('/casas', async (req, res) => {
  try {
    const resultado = await pool.query('SELECT * FROM casas');
    res.json(resultado.rows);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error en la consulta');
  }
});

app.post('/estado', async (req, res) => {
  const { id, estado } = req.body;
  try {
    await pool.query('UPDATE casas SET estado = $1 WHERE id = $2', [estado, id]);
    io.emit('actualizacion');
    res.sendStatus(200);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error actualizando estado');
  }
});

app.post('/comentario', async (req, res) => {
  const { id, comentario } = req.body;
  try {
    await pool.query('UPDATE casas SET comentario = $1 WHERE id = $2', [comentario, id]);
    io.emit('actualizacion');
    res.sendStatus(200);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error guardando comentario');
  }
});

app.post('/asignar', async (req, res) => {
  const { ids, usuario } = req.body;
  try {
    await pool.query(
      'UPDATE casas SET asignado_a = $1 WHERE id = ANY($2::int[])',
      [usuario, ids]
    );
    io.emit('actualizacion');
    res.sendStatus(200);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error asignando casas');
  }
});

app.post('/desasignar', async (req, res) => {
  const { id } = req.body;
  try {
    await pool.query(
      'UPDATE casas SET asignado_a = NULL, estado = NULL, comentario = NULL WHERE id = $1',
      [id]
    );
    io.emit('actualizacion');
    res.sendStatus(200);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error desasignando casa');
  }
});

// Aquí importante: arrancar el servidor con el puerto asignado
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Servidor corriendo en puerto ${PORT}`);
});
