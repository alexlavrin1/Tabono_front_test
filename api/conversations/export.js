import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

function csvCell(val) {
  const s = String(val ?? '');
  return s.includes(',') || s.includes('"') || s.includes('\n')
    ? `"${s.replace(/"/g, '""')}"`
    : s;
}

export default async function handler(req, res) {
  const { data, error } = await supabase
    .from('conversations')
    .select('*')
    .order('timestamp', { ascending: true });

  if (error) return res.status(500).json({ detail: error.message });

  const lines = [
    'conversation_id,timestamp,role,content',
    ...data.map(r =>
      [r.conversation_id, r.timestamp, r.role, r.content].map(csvCell).join(',')
    ),
  ];

  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="conversations.csv"');
  return res.status(200).send(lines.join('\n'));
}
