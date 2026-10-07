const { Client } = require('pg');

const client = new Client({
  user: 'cams_user',
  host: 'localhost',
  database: 'cams_db',
  password: 'cams_password',
  port: 5432,
});

client.connect();

client.query('SELECT p.fen, s.move_order, s.move_uci, s.is_best_move FROM puzzles p JOIN puzzle_solutions s ON p.id = s.puzzle_id ORDER BY p.id, s.move_order LIMIT 10', (err, res) => {
  if (err) throw err;
  for (let row of res.rows) {
    console.log(row);
  }
  client.end();
});
