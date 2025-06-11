// Asumo que tienes algo así:
const express = require('express');
const app = express();
const pool = require('./db'); // tu pool pg o conexión a DB

app.use(express.json());
app.use(express.static('public')); // sirviendo archivos públicos

// Endpoint para casas (admin): retorna todas
app.get('/casas', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM casas');
    res.json(result.rows);
  } catch (e) {
    console.error(e);
    res.status(500).send('Error al obtener casas');
  }
});

// Endpoint para casas (usuario) filtrado por usuario asignado
app.get('/casas', async (req, res) => {
  const usuario = req.query.usuario;
  if (!usuario) {
    try {
      const result = await pool.query('SELECT * FROM casas');
      res.json(result.rows);
    } catch (e) {
      console.error(e);
      res.status(500).send('Error al obtener casas');
    }
  } else {
    try {
      const result = await pool.query('SELECT * FROM casas WHERE asignado_a = $1', [usuario]);
      if (result.rows.length === 0) {
        return res.status(404).send('No hay casas asignadas');
      }
      res.json(result.rows);
    } catch (e) {
      console.error(e);
      res.status(500).send('Error al obtener casas para usuario');
    }
  }
});

// Endpoint para asignar casas
app.post('/asignar', async (req, res) => {
  const { usuario, ids } = req.body;
  if (!usuario || !ids || !Array.isArray(ids)) {
    return res.status(400).send('Faltan datos');
  }
  try {
    const q = 'UPDATE casas SET asignado_a = $1 WHERE id = ANY($2::int[])';
    await pool.query(q, [usuario, ids]);
    res.sendStatus(200);
  } catch (e) {
    console.error(e);
    res.status(500).send('Error al asignar casas');
  }
});

// Endpoint para desasignar casas (borra estado y comentario también)
app.post('/desasignar', async (req, res) => {
  const { ids } = req.body;
  if (!ids || !Array.isArray(ids)) {
    return res.status(400).send('Faltan datos');
  }
  try {
    const q = 'UPDATE casas SET asignado_a = NULL, estado = NULL, comentario = NULL WHERE id = ANY($1::int[])';
    await pool.query(q, [ids]);
    res.sendStatus(200);
  } catch (e) {
    console.error(e);
    res.status(500).send('Error al desasignar casas');
  }
});

// Endpoint para actualizar estado y comentario de casa
app.post('/actualizar', async (req, res) => {
  const { id, estado, comentario } = req.body;
  if (!id || !estado) return res.status(400).send('Faltan datos');
  try {
    const q = 'UPDATE casas SET estado = $1, comentario = $2 WHERE id = $3';
    await pool.query(q, [estado, comentario, id]);
    res.sendStatus(200);
  } catch (e) {
    console.error(e);
    res.status(500).send('Error al actualizar');
  }
});

// Endpoint para estadísticas
app.get('/stats', async (req, res) => {
  try {
    const casasRes = await pool.query('SELECT * FROM casas');
    const casas = casasRes.rows;

    // Comentarios por casa
    const comentarios = casas.map(c => ({
      id: c.id,
      direccion: c.direccion,
      asignado_a: c.asignado_a,
      estado: c.estado,
      comentario: c.comentario
    }));

    // Casas visitadas por persona
    const visitadas = {};
    // Casas asignadas por persona
    const asignadas = {};

    casas.forEach(c => {
      if (c.asignado_a) {
        asignadas[c.asignado_a] = (asignadas[c.asignado_a] || 0) + 1;
        if (c.estado === 'visitada') {
          visitadas[c.asignado_a] = (visitadas[c.asignado_a] || 0) + 1;
        }
      }
    });

    res.json({ comentarios, visitadas, asignadas });
  } catch (e) {
    console.error(e);
    res.status(500).send('Error al obtener estadísticas');
  }
});

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Servidor corriendo en puerto ${port}`));
