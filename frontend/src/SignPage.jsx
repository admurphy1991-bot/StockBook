import React, { useState, useEffect, useRef } from 'react'

const styles = {
  page: { minHeight: '100vh', background: '#eef1f5', padding: '24px 16px', color: '#1a1f27', fontFamily: "'Barlow', sans-serif" },
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 24, color: '#3f5064' },
  sheet: { maxWidth: 640, margin: '0 auto', background: '#fff', borderRadius: 8, padding: '28px 24px', boxShadow: '0 2px 10px rgba(0,0,0,.08)' },
  h1: { fontFamily: "'Barlow Condensed', sans-serif", fontSize: 22, fontWeight: 800, letterSpacing: 0.3, marginBottom: 4 },
  sub: { fontSize: 13, color: '#6a8099', marginBottom: 18 },
  meta: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 14px', fontSize: 13, marginBottom: 18 },
  h2: { fontFamily: "'Barlow Condensed', sans-serif", fontSize: 15, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase', margin: '18px 0 8px' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12.5, marginBottom: 8 },
  th: { border: '1px solid #ccc', padding: '5px 6px', textAlign: 'left', background: '#f3f4f6' },
  td: { border: '1px solid #ccc', padding: '5px 6px' },
  comments: { fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.5, marginBottom: 8 },
  photos: { display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  photo: { width: 100, height: 100, objectFit: 'cover', border: '1px solid #ccc', borderRadius: 4 },
  fieldLabel: { fontSize: 11, fontFamily: "'Barlow Condensed', sans-serif", fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: '#6a8099', marginBottom: 6, display: 'block' },
  input: { width: '100%', border: '1px solid #ccc', borderRadius: 6, padding: '10px 12px', fontSize: 14, color: '#1a1f27', marginBottom: 16 },
  canvasWrap: { display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 18 },
  canvas: { width: '100%', height: 160, background: '#f7f8fa', border: '1px dashed #ccc', borderRadius: 8, touchAction: 'none' },
  clearBtn: { alignSelf: 'flex-start', border: 'none', background: 'none', color: '#1B9ED4', fontFamily: "'Barlow Condensed', sans-serif", fontSize: 12, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase', cursor: 'pointer', padding: '4px 0' },
  submitBtn: (enabled) => ({ width: '100%', border: 'none', background: '#1B9ED4', color: '#fff', borderRadius: 6, padding: 14, fontFamily: "'Barlow Condensed', sans-serif", fontSize: 15, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', cursor: enabled ? 'pointer' : 'not-allowed', opacity: enabled ? 1 : 0.5 }),
  errorMsg: { fontSize: 12.5, color: '#e05252', textAlign: 'center', marginTop: 10 },
  checkCircle: { width: 56, height: 56, borderRadius: '50%', background: 'rgba(76,175,125,.12)', border: '1px solid #4caf7d', color: '#4caf7d', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, margin: '0 auto 14px' },
}

export default function SignPage({ token }) {
  const [status, setStatus] = useState('loading') // loading | notfound | ready | submitting | done
  const [notice, setNotice] = useState('')
  const [entry, setEntry] = useState(null)
  const [clientName, setClientName] = useState('')
  const [signed, setSigned] = useState(false)
  const [error, setError] = useState('')

  const canvasRef = useRef(null)
  const drawingRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    fetch(`/api/dayworks/sign/${token}`)
      .then(async (r) => {
        if (cancelled) return
        if (r.status === 410) { setNotice('This sheet has already been signed. Thanks for confirming it.'); setStatus('notfound'); return }
        if (!r.ok) { setNotice('This link is invalid or has expired.'); setStatus('notfound'); return }
        const data = await r.json()
        setEntry(data)
        setClientName(data.client_name || '')
        setStatus('ready')
      })
      .catch(() => { if (!cancelled) { setNotice('Could not load this sheet — check your connection and try again.'); setStatus('notfound') } })
    return () => { cancelled = true }
  }, [token])

  function getPos(e) {
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY }
  }
  function onSigDown(e) {
    drawingRef.current = true
    const ctx = canvasRef.current.getContext('2d')
    const p = getPos(e)
    ctx.strokeStyle = '#1a1f27'; ctx.lineWidth = 2.2; ctx.lineCap = 'round'
    ctx.beginPath(); ctx.moveTo(p.x, p.y)
    setSigned(true)
  }
  function onSigMove(e) {
    if (!drawingRef.current) return
    const ctx = canvasRef.current.getContext('2d')
    const p = getPos(e)
    ctx.lineTo(p.x, p.y); ctx.stroke()
  }
  function onSigUp() { drawingRef.current = false }
  function clearSignature() {
    const canvas = canvasRef.current
    if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height)
    setSigned(false)
  }

  async function submit() {
    if (!signed) { setError('Please sign before confirming.'); return }
    setError('')
    setStatus('submitting')
    try {
      const r = await fetch(`/api/dayworks/sign/${token}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: clientName || null, signature_data_url: canvasRef.current.toDataURL() }),
      })
      if (!r.ok) throw new Error('failed')
      setStatus('done')
    } catch (e) {
      setError('Something went wrong submitting your signature — please try again.')
      setStatus('ready')
    }
  }

  if (status === 'loading') {
    return <div style={styles.center}>Loading sheet…</div>
  }

  if (status === 'notfound') {
    return <div style={styles.center}>{notice}</div>
  }

  if (status === 'done') {
    return (
      <div style={styles.page}>
        <div style={{ ...styles.sheet, textAlign: 'center', padding: '48px 24px' }}>
          <div style={styles.checkCircle}>✓</div>
          <div style={styles.h1}>Thanks, you're all signed off</div>
          <div style={{ fontSize: 14, color: '#6a8099', marginTop: 8 }}>
            Your signature has been recorded against this Day Works sheet. You can close this page now.
          </div>
        </div>
      </div>
    )
  }

  const labourRows = entry.labour_rows || []
  const materialRows = entry.material_rows || []
  const photos = entry.photos || []

  return (
    <div style={styles.page}>
      <div style={styles.sheet}>
        <div style={styles.h1}>{entry.job}</div>
        <div style={styles.sub}>
          Day Works sheet{entry.variation === 'Yes' && entry.vo_number ? ` · ${entry.vo_number}` : ''} — please review and sign below
        </div>

        <div style={styles.meta}>
          <div><b>Date:</b> {entry.entry_date}</div>
          <div><b>Location:</b> {entry.location || '—'}</div>
        </div>

        <div style={styles.h2}>Labour</div>
        {labourRows.length === 0 ? (
          <div style={{ fontSize: 13, color: '#6a8099', marginBottom: 8 }}>No labour logged.</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Name</th><th style={styles.th}>Activity</th>
                <th style={styles.th}>Start</th><th style={styles.th}>Finish</th><th style={styles.th}>Hours</th>
              </tr>
            </thead>
            <tbody>
              {labourRows.map((row, i) => (
                <tr key={i}>
                  <td style={styles.td}>{row.name}</td><td style={styles.td}>{row.activity}</td>
                  <td style={styles.td}>{row.start}</td><td style={styles.td}>{row.end}</td><td style={styles.td}>{row.hoursLabel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div style={styles.h2}>Materials</div>
        {materialRows.length === 0 ? (
          <div style={{ fontSize: 13, color: '#6a8099', marginBottom: 8 }}>No materials logged.</div>
        ) : (
          <table style={styles.table}>
            <thead><tr><th style={styles.th}>Item</th><th style={styles.th}>Unit</th><th style={styles.th}>Qty</th></tr></thead>
            <tbody>
              {materialRows.map((row, i) => (
                <tr key={i}><td style={styles.td}>{row.item}</td><td style={styles.td}>{row.unit}</td><td style={styles.td}>{row.qty}</td></tr>
              ))}
            </tbody>
          </table>
        )}

        {entry.comments && (<>
          <div style={styles.h2}>Comments</div>
          <div style={styles.comments}>{entry.comments}</div>
        </>)}

        {photos.length > 0 && (<>
          <div style={styles.h2}>Photos ({photos.length})</div>
          <div style={styles.photos}>
            {photos.map((p) => p.src && <img key={p.id} src={p.src} style={styles.photo} />)}
          </div>
        </>)}

        <div style={styles.h2}>Client Sign-off</div>
        <label style={styles.fieldLabel}>Your name</label>
        <input style={styles.input} value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="Who is signing?" />

        <label style={styles.fieldLabel}>Signature</label>
        <div style={styles.canvasWrap}>
          <canvas
            ref={canvasRef} width={560} height={160}
            onPointerDown={onSigDown} onPointerMove={onSigMove} onPointerUp={onSigUp} onPointerLeave={onSigUp}
            style={styles.canvas}
          />
          <button onClick={clearSignature} style={styles.clearBtn}>Clear</button>
        </div>

        <button onClick={submit} disabled={status === 'submitting'} style={styles.submitBtn(status !== 'submitting')}>
          {status === 'submitting' ? 'Submitting…' : 'Confirm & Sign'}
        </button>
        {error && <div style={styles.errorMsg}>{error}</div>}
      </div>
    </div>
  )
}
