const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const db = require('./db');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static('public'));
app.use(express.json());

app.get('/casas', async (req, res) => {
  const result = await db.query('SELECT * FROM casas');
  res.json(result.rows);
});

app.post('/casas/:id/estado', async (req, res) => {
  const { id } = req.params;
  const { estado, comentario, actualizado_por } = req.body;
  const result = await db.query(
    `UPDATE casas SET estado=$1, comentario=$2, actualizado_por=$3, updated_at=NOW()
     WHERE id=$4 RETURNING *`,
    [estado, comentario, actualizado_por, id]
  );
  const actualizada = result.rows[0];
  io.emit('casaActualizada', actualizada);
  res.json(actualizada);
});

io.on('connection', socket => {
  console.log('cliente conectado');
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`Servidor en puerto ${PORT}`));
