import { createClient } from '@supabase/supabase-js';
import busboy from 'busboy';

export const config = { api: { bodyParser: false } };

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

function parseMultipart(req) {
  return new Promise((resolve, reject) => {
    const bb = busboy({ headers: req.headers });
    let result = null;

    bb.on('file', (_field, stream, info) => {
      const chunks = [];
      stream.on('data', chunk => chunks.push(chunk));
      stream.on('end', () => {
        result = {
          filename: info.filename,
          mimetype: info.mimeType || 'application/octet-stream',
          buffer: Buffer.concat(chunks),
        };
      });
    });

    bb.on('finish', () => result ? resolve(result) : reject(new Error('No file in request')));
    bb.on('error', reject);
    req.pipe(bb);
  });
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  let file;
  try {
    file = await parseMultipart(req);
  } catch (e) {
    return res.status(400).json({ detail: e.message });
  }

  // Save to Supabase Storage
  const storagePath = `${Date.now()}-${file.filename}`;
  const { error: storageErr } = await supabase.storage
    .from('uploads')
    .upload(storagePath, file.buffer, { contentType: file.mimetype });

  if (storageErr) {
    return res.status(500).json({ detail: storageErr.message });
  }

  // Upload to OpenAI Files API so the agent can read it
  const form = new FormData();
  form.append('file', new Blob([file.buffer], { type: file.mimetype }), file.filename);
  form.append('purpose', 'user_data');

  const openaiResp = await fetch('https://api.openai.com/v1/files', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${process.env.OPENAI_API_KEY}` },
    body: form,
  });

  if (!openaiResp.ok) {
    return res.status(openaiResp.status).json({ detail: await openaiResp.text() });
  }

  const { id } = await openaiResp.json();
  return res.status(200).json({ file_id: id, filename: file.filename, size: file.buffer.length });
}
