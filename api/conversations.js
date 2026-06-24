import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();

  const { data, error } = await supabase
    .from('conversations')
    .select('*')
    .order('timestamp', { ascending: true });

  if (error) return res.status(500).json({ detail: error.message });

  const groups = {};
  for (const row of data) {
    if (!groups[row.conversation_id]) {
      groups[row.conversation_id] = {
        id: row.conversation_id,
        started_at: row.timestamp,
        messages: [],
      };
    }
    groups[row.conversation_id].messages.push({
      role: row.role,
      content: row.content,
      timestamp: row.timestamp,
    });
  }

  const result = Object.values(groups).sort(
    (a, b) => new Date(b.started_at) - new Date(a.started_at)
  );

  return res.status(200).json(result);
}
