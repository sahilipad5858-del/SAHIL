import { useState } from 'react'
import './App.css'

function App() {
  const [step, setStep] = useState(1) // 1: Upload, 2: Review Fields, 3: Edit Email, 4: Preview
  const [file, setFile] = useState(null)
  const [fileId, setFileId] = useState(null)
  const [filename, setFilename] = useState('')
  const [poData, setPoData] = useState({})
  const [emailDraft, setEmailDraft] = useState({ to: '', subject: '', body: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sendResult, setSendResult] = useState(null)

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

  const handleSend = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/send-email?file_id=${fileId || ''}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: emailDraft.to,
          subject: emailDraft.subject,
          body: emailDraft.body,
          attachment_name: filename ? `PO_${filename}` : undefined,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Send failed')
      setSendResult(data)
      setStep(5)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
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
          <div className="upload-area" onClick={() => document.getElementById('file-input').click()}>
            <input
              id="file-input"
              type="file"
              accept=".pdf"
              onChange={e => setFile(e.target.files[0])}
              style={{ display: 'none' }}
            />
            {file ? (
              <p className="file-name">{file.name}</p>
            ) : (
              <p>Click to select a PDF file</p>
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
              { key: 'po_number', label: 'PO Number' },
              { key: 'po_date', label: 'PO Date' },
              { key: 'delivery_date', label: 'Delivery Date' },
              { key: 'payment_terms', label: 'Payment Terms' },
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
            <div className="preview-row"><strong>Subject:</strong> {emailDraft.subject}</div>
            <div className="preview-row"><strong>Attachment:</strong> {filename ? `PO_${filename}` : 'None'}</div>
            <hr />
            <pre className="preview-body">{emailDraft.body}</pre>
          </div>
          <div className="btn-group">
            <button className="btn secondary" onClick={() => setStep(3)}>Back</button>
            <button className="btn danger" onClick={handleSend} disabled={loading}>
              {loading ? 'Sending...' : 'Approve & Send'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Success */}
      {step === 5 && (
        <div className="card success-card">
          <h2>Email Sent Successfully!</h2>
          <p>{sendResult?.message}</p>
          <button className="btn primary" onClick={reset}>Send Another PO</button>
        </div>
      )}
    </div>
  )
}

export default App
