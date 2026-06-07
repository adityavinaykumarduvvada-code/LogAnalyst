const BASE = '/api'

export async function fetchStatus() {
  const res = await fetch(`${BASE}/status`)
  return res.json()
}

export async function uploadFiles(fileList) {
  const formData = new FormData()
  for (const file of fileList) {
    formData.append('files', file)
  }
  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    body: formData, 
  })
  return res.json()
}

export async function askQuestion(question) {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return res.json()
}
