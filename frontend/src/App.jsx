import { useState, useCallback } from 'react'
import './App.css'

function App() {
  const [step, setStep] = useState(1)
  const [file, setFile] = useState(null)
  const [fileId, setFileId] = useState(null)
  const [filename, setFilename] = useState('')
  const [poData, setPoData] = useState({})
  const [emailDraft, setEmailDraft] = useState({ to: '', subject: '', body: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sendResult, setSendResult] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [showRawText, setShowRawText] = useState(false)

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile)
    } else {
      setError('Only PDF files are accepted')
    }
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/upload-po', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setFileId(data.file_id)
      setFilename(data.filename)
      setPoData(data.po_data)
      setEmailDraft({
        to: data.email_draft.to,
        cc: data.email_draft.cc || '',
        subject: data.email_draft.subject,
        body: data.email_draft.body,
      })
      setStep(2)
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

  const handleSend = () => {
    const to = encodeURIComponent(emailDraft.to || '')
    const cc = encodeURIComponent(emailDraft.cc || '')
    const subject = encodeURIComponent(emailDraft.subject || '')
    const body = encodeURIComponent(emailDraft.body || '')
    const mailtoUrl = `mailto:${to}?cc=${cc}&subject=${subject}&body=${body}`
    window.location.href = mailtoUrl
  }

  const reset = () => {
    setStep(1)
    setFile(null)
    setFileId(null)
    setFilename('')
    setPoData({})
    setEmailDraft({ to: '', subject: '', body: '' })
    setError('')
    setSendResult(null)
  }

  return (
    <div className="app">
      <header className="header">
        <h1>PO Mailer</h1>
        <p>Upload a Purchase Order, review extracted data, and send it via email</p>
      </header>

      <div className="steps">
        {['Upload PO', 'Review Fields', 'Edit Email', 'Preview & Send'].map((label, i) => (
          <div key={i} className={`step ${step > i + 1 ? 'done' : ''} ${step === i + 1 ? 'active' : ''}`}>
            <span className="step-num">{i + 1}</span>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      {/* STEP 1: Upload */}
      {step === 1 && (
        <div className="card">
          <h2>Upload Purchase Order</h2>
          <div
            className={`upload-area ${dragOver ? 'drag-over' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input').click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".pdf"
              onChange={e => setFile(e.target.files[0])}
              style={{ display: 'none' }}
            />
            {file ? (
              <>
                <div className="upload-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                  </svg>
                </div>
                <p className="file-name">{file.name}</p>
                <p className="file-hint">Click or drop to replace</p>
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
          <button className="btn primary" onClick={handleUpload} disabled={!file || loading}>
            {loading ? 'Processing...' : 'Upload & Extract'}
          </button>
        </div>
      )}

      {/* STEP 2: Review Fields */}
      {step === 2 && (
        <div className="card">
          <h2>Extracted PO Fields</h2>
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
                  placeholder={`Enter ${label}`}
                />
              </div>
            ))}
          </div>
          {poData.raw_text && (
            <div className="raw-text-section">
              <button className="btn-text" onClick={() => setShowRawText(!showRawText)}>
                {showRawText ? 'Hide' : 'Show'} Raw Extracted Text
              </button>
              {showRawText && (
                <pre className="raw-text-box">{poData.raw_text}</pre>
              )}
            </div>
          )}
          <div className="btn-group">
            <button className="btn secondary" onClick={() => setStep(1)}>Back</button>
            <button className="btn primary" onClick={() => setStep(3)}>Next: Edit Email</button>
          </div>
        </div>
      )}

      {/* STEP 3: Edit Email */}
      {step === 3 && (
        <div className="card">
          <h2>Edit Email Draft</h2>
          <div className="email-form">
            <div className="field">
              <label>To</label>
              <input
                type="email"
                value={emailDraft.to}
                onChange={e => handleEmailChange('to', e.target.value)}
                placeholder="recipient@example.com"
              />
            </div>
            <div className="field">
              <label>CC</label>
              <input
                type="text"
                value={emailDraft.cc || ''}
                onChange={e => handleEmailChange('cc', e.target.value)}
                placeholder="cc1@example.com, cc2@example.com"
              />
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
                rows={12}
                value={emailDraft.body}
                onChange={e => handleEmailChange('body', e.target.value)}
              />
            </div>
          </div>
          <div className="btn-group">
            <button className="btn secondary" onClick={() => setStep(2)}>Back</button>
            <button className="btn primary" onClick={() => setStep(4)}>Next: Preview</button>
          </div>
        </div>
      )}

      {/* STEP 4: Preview */}
      {step === 4 && (
        <div className="card">
          <h2>Email Preview</h2>
          <div className="preview-box">
            <div className="preview-row"><strong>To:</strong> {emailDraft.to}</div>
            {emailDraft.cc && <div className="preview-row"><strong>CC:</strong> {emailDraft.cc}</div>}
            <div className="preview-row"><strong>Subject:</strong> {emailDraft.subject}</div>
            <div className="preview-row"><strong>Attachment:</strong> {filename ? `PO_${filename}` : 'None'}</div>
            <hr />
            <pre className="preview-body">{emailDraft.body}</pre>
          </div>
          {filename && (
            <div className="attachment-note">
              <strong>Attachment:</strong> PO_{filename.replace(/[^a-zA-Z0-9._-]/g, '_')} (attach manually in email app)
            </div>
          )}
          <div className="btn-group">
            <button className="btn secondary" onClick={() => setStep(3)}>Back</button>
            <button className="btn primary" onClick={handleSend}>
              Open in Email App
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
