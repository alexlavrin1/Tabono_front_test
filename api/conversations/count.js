import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export default async function handler(req, res) {
  const { count, error } = await supabase
    .from('conversations')
    .select('*', { count: 'exact', head: true });

  if (error) return res.status(500).json({ detail: error.message });

  return res.status(200).json({ rows: count ?? 0 });
}
