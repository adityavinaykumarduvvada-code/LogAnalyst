const BASE = '/api'

// Parse a response as JSON, but never throw on HTML error pages
// (e.g. a 502/504 from the hosting proxy when the server times out).
async function readJson(res) {
  const text = await res.text()
  try {
    return JSON.parse(text)
  } catch {
    const hint =
      res.status === 502 || res.status === 504
        ? 'The server took too long to respond. Please try again in a moment.'
        : 'The server returned an unexpected response.'
    return { error: `${hint} (HTTP ${res.status})` }
  }
}

export async function fetchStatus() {
  const res = await fetch(`${BASE}/status`)
  return readJson(res)
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
  return readJson(res)
}

export async function askQuestion(question) {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return readJson(res)
}
