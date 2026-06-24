import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  const { conversation_id, messages } = req.body || {};
  if (!messages?.length) return res.status(200).json({ ok: true, written: 0 });

  const rows = messages.map(m => ({
    conversation_id,
    timestamp: m.timestamp || new Date().toISOString(),
    role: m.role,
    content: m.content,
  }));

  const { error } = await supabase.from('conversations').insert(rows);
  if (error) return res.status(500).json({ detail: error.message });

  return res.status(200).json({ ok: true, written: rows.length });
}
