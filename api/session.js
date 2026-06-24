export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();

  const { user_id } = req.body || {};

  const resp = await fetch('https://api.openai.com/v1/chatkit/sessions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
      'OpenAI-Beta': 'chatkit_beta=v1',
    },
    body: JSON.stringify({
      workflow: { id: process.env.WORKFLOW_ID },
      user: user_id || 'default-user',
    }),
  });

  if (!resp.ok) {
    return res.status(resp.status).json({ detail: await resp.text() });
  }

  return res.status(200).json(await resp.json());
}
