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

// Obtener casas solo asignadas a usuario
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

// Obtener todas las casas (admin)
app.get('/casas', async (req, res) => {
  try {
    const resultado = await pool.query('SELECT * FROM casas');
    res.json(resultado.rows);
  } catch (error) {
    console.error(error);
    res.status(500).send('Error en la consulta');
  }
});

// Cambiar estado
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

// Guardar comentario
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

// Asignar casas (admin)
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

// Desasignar casas (admin)
app.post('/desasignar', async (req, res) => {
  const { ids } = req.body; // ahora un array
  await pool.query(
    'UPDATE casas SET asignado_a = NULL, estado = NULL, comentario = NULL WHERE id = ANY($1::int[])',
    [ids]
  );
  io.emit('actualizacion');
  res.sendStatus(200);
});


const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Servidor corriendo en puerto ${PORT}`);
});
