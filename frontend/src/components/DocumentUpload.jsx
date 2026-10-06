import { useRef, useState } from 'react'
import './DocumentUpload.css'

function DocumentUpload({
  documentError,
  documentName,
  documentStatus,
  documentUploadError,
  isUploading,
  isReady,
  onUpload,
}) {
  const inputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const processing = ['PROCESSING', 'INDEXING'].includes(documentStatus)
  const busy = isUploading || processing || documentStatus === 'checking'
  const ready = ['READY', 'INDEXED'].includes(documentStatus)
  let statusMessage = `Upload a PDF, DOCX, XLS, or XLSX to ask questions about its content.`

  if (documentUploadError) {
    statusMessage = `Upload failed: ${documentUploadError}${ready ? ` ${documentName || 'Your previous document'} is still ready.` : ''}`
  } else if (isUploading) {
    statusMessage = 'Preparing your document… You can keep asking normal tutor questions.'
  } else if (processing) {
    statusMessage = 'Your document is still being prepared. You can keep asking normal tutor questions.'
  } else if (documentStatus === 'checking') {
    statusMessage = 'Checking document status…'
  } else if (ready) {
    statusMessage = `${documentName || 'Your document'} is ready for questions.`
  } else if (documentStatus === 'FAILED') {
    statusMessage = documentError || 'The document could not be prepared. Please try again.'
  } else if (documentStatus === 'unavailable') {
    statusMessage = documentError || 'Document status is unavailable.'
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (!selectedFile || busy || !isReady) return
    onUpload(selectedFile)
    setSelectedFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <form className="document-upload" onSubmit={handleSubmit}>
      <div className="document-upload-copy">
        <p className="document-upload-title">Ask about a document</p>
        <p className="document-upload-status" role="status" aria-live="polite">
          {statusMessage}
        </p>
      </div>
      <input
        ref={inputRef}
        aria-label="Choose a document to upload"
        accept=".pdf,.docx,.xls,.xlsx"
        type="file"
        onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
        disabled={busy || !isReady}
      />
      <button
        className="document-upload-button"
        type="submit"
        disabled={!selectedFile || busy || !isReady}
      >
        {isUploading || processing ? 'Preparing…' : 'Upload document'}
      </button>
    </form>
  )
}

export default DocumentUpload
