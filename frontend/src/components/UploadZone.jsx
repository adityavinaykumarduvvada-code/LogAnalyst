import { useState, useRef } from 'react'
import { uploadFiles } from '../api.js'

export default function UploadZone({ onUploaded }) {
  const [headline, setHeadline] = useState(
    "Drop your log files here, or click to browse"
  )
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef(null)

  async function handleFiles(fileList) {
    if (!fileList || fileList.length === 0) return
    setHeadline('Reading your files and building the index…')
    try {
      const result = await uploadFiles(fileList)
      if (result.error) {
        setHeadline(`That didn't work: ${result.error}`)
      } else {
        setHeadline(
          `Added ${result.entries_indexed} log lines from ${result.saved_files.length} file(s) — drop more anytime`
        )
        onUploaded() // tell App.jsx to refresh the status bar
      }
    } catch (err) {
      setHeadline(`That didn't work: ${err.message}`)
    }
  }

  return (
    <div
      className={`upload-zone ${isDragOver ? 'dragover' : ''}`}
      onClick={() => fileInputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setIsDragOver(false)
        handleFiles(e.dataTransfer.files)
      }}
    >
      <div className="headline">{headline}</div>
      <div className="sub">.log · .txt · .csv · .json · or a .zip with several files inside</div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".log,.txt,.csv,.json,.zip"
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}
