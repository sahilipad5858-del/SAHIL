import { useState, useCallback } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [fileId, setFileId] = useState(null)
  const [filename, setFilename] = useState('')
  const [poData, setPoData] = useState({})
  const [emailDraft, setEmailDraft] = useState({ to: '', cc: '', subject: '', body: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile)
      autoUpload(droppedFile)
    } else {
      setError('Only PDF files are accepted')
    }
  }, [])

  const handleFileSelect = (e) => {
    const selected = e.target.files[0]
    if (selected) {
      setFile(selected)
      autoUpload(selected)
    }
  }

  const autoUpload = async (uploadFile) => {
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      const res = await fetch('/api/upload-po', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setFileId(data.file_id)
      setFilename(data.filename)
      setPoData(data.po_data)
      setEmailDraft({
        to: data.email_draft.to || '',
        cc: data.email_draft.cc || '',
        subject: data.email_draft.subject || '',
        body: data.email_draft.body || '',
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFieldChange = (field, value) => {
    setPoData(prev => ({ ...prev, [field]: value }))
  }

  const handleEmailChange = (field, value) => {
    setEmailDraft(prev => ({ ...prev, [field]: value }))
  }

  const handleSend = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/send-email?file_id=${fileId || ''}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: emailDraft.to,
          cc: emailDraft.cc,
          subject: emailDraft.subject,
          body: emailDraft.body,
          attachment_name: filename ? `PO_${filename.replace(/[^a-zA-Z0-9._-]/g, '_')}` : undefined,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Send failed')
      setSent(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setFile(null)
    setFileId(null)
    setFilename('')
    setPoData({})
    setEmailDraft({ to: '', cc: '', subject: '', body: '' })
    setError('')
    setSent(false)
  }

  if (sent) {
    return (
      <div className="app">
        <div className="success-card">
          <h2>Email Sent Successfully!</h2>
          <p>Purchase Order has been sent to {emailDraft.to}</p>
          {emailDraft.cc && <p>CC: {emailDraft.cc}</p>}
          <button className="btn primary" onClick={handleReset}>Send Another PO</button>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="header">
        <h1>PO Mailer</h1>
        <p>Upload a Purchase Order — review and send in one place</p>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="card">
        <h2>Upload Purchase Order</h2>
        <div
          className={`upload-area ${dragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !file && document.getElementById('file-input').click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          {file ? (
            <>
              <div className="upload-icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
              </div>
              <p className="file-name">{file.name}</p>
              <button className="btn-text" onClick={(e) => { e.stopPropagation(); handleReset(); }}>Remove</button>
            </>
          ) : (
            <>
              <div className="upload-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </div>
              <p>Drag & drop a PDF here, or <span className="browse-link">browse</span></p>
            </>
          )}
        </div>
        {loading && <div className="loading">Processing PO...</div>}
      </div>

      {fileId && (
        <>
          <div className="card">
            <h2>Extracted Fields</h2>
            <div className="fields-grid">
              {[
                { key: 'vendor_name', label: 'Vendor Name' },
                { key: 'buyer_name', label: 'Buyer Name' },
                { key: 'po_number', label: 'PO Number' },
                { key: 'po_date', label: 'PO Date' },
                { key: 'plant', label: 'Plant' },
                { key: 'delivery_date', label: 'Delivery Date' },
                { key: 'shipping_address', label: 'Shipping Address' },
                { key: 'vendor_email', label: 'Vendor Email' },
              ].map(({ key, label }) => (
                <div className="field" key={key}>
                  <label>{label}</label>
                  <input
                    type="text"
                    value={poData[key] || ''}
                    onChange={e => handleFieldChange(key, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>Email Preview</h2>
            <div className="email-form">
              <div className="field-row">
                <div className="field">
                  <label>To</label>
                  <input
                    type="email"
                    value={emailDraft.to}
                    onChange={e => handleEmailChange('to', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>CC</label>
                  <input
                    type="text"
                    value={emailDraft.cc}
                    onChange={e => handleEmailChange('cc', e.target.value)}
                  />
                </div>
              </div>
              <div className="field">
                <label>Subject</label>
                <input
                  type="text"
                  value={emailDraft.subject}
                  onChange={e => handleEmailChange('subject', e.target.value)}
                />
              </div>
              <div className="field">
                <label>Body</label>
                <textarea
                  rows={14}
                  value={emailDraft.body}
                  onChange={e => handleEmailChange('body', e.target.value)}
                />
              </div>
            </div>
            <div className="send-bar">
              <span className="attachment-badge">PDF attached</span>
              <button className="btn primary btn-send" onClick={handleSend} disabled={loading}>
                {loading ? 'Sending...' : 'Approve & Send'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default App
