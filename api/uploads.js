import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();

  const { conversation_id } = req.query;
  if (!conversation_id) return res.status(400).json({ detail: 'conversation_id required' });

  const { data, error } = await supabase
    .from('uploaded_files')
    .select('filename, file_id, size, timestamp')
    .eq('conversation_id', conversation_id)
    .order('timestamp', { ascending: true });

  if (error) return res.status(500).json({ detail: error.message });

  return res.status(200).json(data);
}
