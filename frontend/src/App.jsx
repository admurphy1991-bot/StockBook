import { useState, useEffect, useRef, useCallback } from 'react'

// ── Styles ──────────────────────────────────────────────────────────────────
const S = {
  app: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg)',
  },
  header: {
    background: 'var(--surface)',
    borderBottom: '2px solid var(--accent)',
    padding: '0 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 64,
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  logo: {
    fontFamily: 'var(--font-head)',
    fontSize: 26,
    fontWeight: 800,
    letterSpacing: 2,
    color: 'var(--accent)',
    textTransform: 'uppercase',
  },
  logoSub: {
    fontFamily: 'var(--font-head)',
    fontSize: 13,
    color: 'var(--muted)',
    letterSpacing: 3,
    textTransform: 'uppercase',
    marginLeft: 2,
  },
  tabs: {
    display: 'flex',
    gap: 4,
  },
  tab: (active) => ({
    padding: '8px 20px',
    background: active ? 'var(--accent)' : 'transparent',
    color: active ? '#0f1115' : 'var(--muted)',
    fontFamily: 'var(--font-head)',
    fontWeight: 700,
    fontSize: 15,
    letterSpacing: 1,
    textTransform: 'uppercase',
    border: active ? 'none' : '1px solid var(--border)',
    borderRadius: 4,
    transition: 'all .15s',
  }),
  main: {
    flex: 1,
    maxWidth: 700,
    width: '100%',
    margin: '0 auto',
    padding: '32px 20px',
  },

  // Voice section
  voiceCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: 32,
    marginBottom: 24,
    textAlign: 'center',
  },
  voiceTitle: {
    fontFamily: 'var(--font-head)',
    fontSize: 22,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: 'var(--text)',
    marginBottom: 6,
  },
  voiceHint: {
    color: 'var(--muted)',
    fontSize: 14,
    marginBottom: 28,
    lineHeight: 1.6,
  },
  micBtn: (listening) => ({
    width: 96,
    height: 96,
    borderRadius: '50%',
    background: listening ? 'var(--danger)' : 'var(--accent)',
    color: listening ? '#fff' : '#0f1115',
    fontSize: 36,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 20px',
    transition: 'all .2s',
    boxShadow: listening
      ? '0 0 0 12px rgba(224,82,82,0.15), 0 0 0 24px rgba(224,82,82,0.07)'
      : '0 4px 20px rgba(245,166,35,0.3)',
    animation: listening ? 'pulse 1.4s ease-in-out infinite' : 'none',
  }),
  transcript: {
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: '14px 18px',
    marginTop: 16,
    color: 'var(--text)',
    fontSize: 15,
    lineHeight: 1.6,
    minHeight: 52,
    textAlign: 'left',
  },

  // State chips
  chip: (color) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '3px 10px',
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    fontFamily: 'var(--font-head)',
    letterSpacing: .5,
    background: color === 'orange' ? 'rgba(245,166,35,.15)' : color === 'green' ? 'rgba(76,175,125,.15)' : 'rgba(224,82,82,.15)',
    color: color === 'orange' ? 'var(--accent)' : color === 'green' ? 'var(--success)' : 'var(--danger)',
    border: `1px solid ${color === 'orange' ? 'rgba(245,166,35,.3)' : color === 'green' ? 'rgba(76,175,125,.3)' : 'rgba(224,82,82,.3)'}`,
  }),

  // Confirm card
  confirmCard: {
    background: 'var(--surface)',
    border: '1px solid var(--accent)',
    borderRadius: 12,
    padding: 28,
    marginBottom: 24,
  },
  confirmTitle: {
    fontFamily: 'var(--font-head)',
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginBottom: 20,
    color: 'var(--accent)',
  },
  field: {
    marginBottom: 14,
  },
  fieldLabel: {
    fontSize: 11,
    fontFamily: 'var(--font-head)',
    fontWeight: 600,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    color: 'var(--muted)',
    marginBottom: 4,
    display: 'block',
  },
  fieldInput: {
    width: '100%',
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    padding: '10px 14px',
    color: 'var(--text)',
    fontSize: 15,
    transition: 'border-color .15s',
  },
  unitHint: {
    display: 'inline-block',
    marginLeft: 10,
    fontSize: 12,
    color: 'var(--accent)',
    fontFamily: 'var(--font-head)',
    fontWeight: 600,
    letterSpacing: .5,
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 14,
  },
  btnRow: {
    display: 'flex',
    gap: 10,
    marginTop: 20,
  },
  btnPrimary: {
    flex: 1,
    padding: '13px 0',
    background: 'var(--accent)',
    color: '#0f1115',
    fontFamily: 'var(--font-head)',
    fontSize: 16,
    fontWeight: 800,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    borderRadius: 6,
    transition: 'background .15s',
  },
  btnSecondary: {
    padding: '13px 22px',
    background: 'transparent',
    color: 'var(--muted)',
    fontFamily: 'var(--font-head)',
    fontSize: 15,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    borderRadius: 6,
    border: '1px solid var(--border)',
    transition: 'all .15s',
  },

  // Disambiguation
  disambigCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: 28,
    marginBottom: 24,
  },
  productOption: (selected) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    padding: '14px 16px',
    background: selected ? 'rgba(245,166,35,.08)' : 'var(--surface2)',
    border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
    borderRadius: 8,
    marginBottom: 10,
    cursor: 'pointer',
    transition: 'all .15s',
  }),
  productCode: {
    fontFamily: 'var(--font-head)',
    fontSize: 20,
    fontWeight: 700,
    color: 'var(--accent)',
    minWidth: 100,
  },
  productDesc: {
    fontSize: 14,
    color: 'var(--text)',
    lineHeight: 1.4,
  },
  productSupplier: {
    fontSize: 12,
    color: 'var(--muted)',
    marginTop: 2,
  },

  // Log
  logCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    overflow: 'hidden',
  },
  logHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border)',
  },
  logTitle: {
    fontFamily: 'var(--font-head)',
    fontSize: 16,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: 'var(--muted)',
  },
  exportBtn: {
    padding: '7px 16px',
    background: 'var(--accent)',
    color: '#0f1115',
    fontFamily: 'var(--font-head)',
    fontSize: 13,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    borderRadius: 4,
  },
  logRow: {
    display: 'grid',
    gridTemplateColumns: '110px 90px 80px 1fr 60px 80px',
    gap: 12,
    padding: '14px 20px',
    borderBottom: '1px solid var(--border)',
    alignItems: 'center',
    fontSize: 13,
  },
  logHead: {
    fontFamily: 'var(--font-head)',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    color: 'var(--muted)',
  },
  deleteBtn: {
    padding: '4px 8px',
    background: 'transparent',
    color: 'var(--danger)',
    fontSize: 16,
    borderRadius: 4,
    border: '1px solid transparent',
    transition: 'all .15s',
  },
  empty: {
    padding: '40px 20px',
    textAlign: 'center',
    color: 'var(--muted)',
    fontFamily: 'var(--font-head)',
    fontSize: 16,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  toast: (show) => ({
    position: 'fixed',
    bottom: 32,
    left: '50%',
    transform: `translateX(-50%) translateY(${show ? 0 : 80}px)`,
    opacity: show ? 1 : 0,
    background: 'var(--success)',
    color: '#0f1115',
    padding: '12px 28px',
    borderRadius: 8,
    fontFamily: 'var(--font-head)',
    fontWeight: 700,
    fontSize: 15,
    letterSpacing: 1,
    textTransform: 'uppercase',
    transition: 'all .3s',
    zIndex: 999,
    pointerEvents: 'none',
  }),
  processing: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: '20px 0',
    color: 'var(--muted)',
    fontFamily: 'var(--font-head)',
    letterSpacing: 1,
    textTransform: 'uppercase',
    fontSize: 14,
  },
  spinner: {
    width: 20,
    height: 20,
    border: '2px solid var(--border)',
    borderTop: '2px solid var(--accent)',
    borderRadius: '50%',
    animation: 'spin .7s linear infinite',
  },
}

// ── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState('capture')
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [processing, setProcessing] = useState(false)
  const [matchResult, setMatchResult] = useState(null)   // AI response
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [form, setForm] = useState({ job: '', quantity: '', comments: '' })
  const [entries, setEntries] = useState([])
  const [toast, setToast] = useState('')
  const [toastShow, setToastShow] = useState(false)
  const recognitionRef = useRef(null)

  // Load entries on mount
  useEffect(() => { loadEntries() }, [])

  async function loadEntries() {
    try {
      const r = await fetch('/api/entries')
      const data = await r.json()
      setEntries(data)
    } catch {}
  }

  // ── Voice ────────────────────────────────────────────────────────────────
  const transcriptRef = useRef('')
  const langRef = useRef('en-NZ')
  const recognitionRef2 = useRef(null)

  function startListening() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { alert('Speech recognition not supported. Try Chrome on Android or desktop.'); return }

    transcriptRef.current = ''
    langRef.current = 'en-NZ'

    // Start two recognisers in parallel — English and Filipino
    // Whichever gets a result first wins
    let settled = false

    function makeRec(lang) {
      const rec = new SR()
      rec.continuous = true
      rec.interimResults = true
      rec.lang = lang
      rec.onstart = () => setListening(true)
      rec.onresult = (e) => {
        if (settled) return
        const t = Array.from(e.results).map(r => r[0].transcript).join('')
        if (t.trim().length > 3) {
          settled = true
          langRef.current = lang
        }
        transcriptRef.current = t
        setTranscript(t)
      }
      rec.onerror = () => {}
      return rec
    }

    const recEN = makeRec('en-NZ')
    const recFIL = makeRec('fil-PH')
    recognitionRef.current = recEN
    recognitionRef2.current = recFIL

    try { recEN.start() } catch(e) {}
    // Slight delay so browsers don't block two simultaneous mic requests
    setTimeout(() => { try { recFIL.start() } catch(e) {} }, 200)
  }

  function stopListening() {
    try { recognitionRef.current?.stop() } catch(e) {}
    try { recognitionRef2.current?.stop() } catch(e) {}
    setListening(false)
    if (transcriptRef.current.trim()) handleTranscript(transcriptRef.current, langRef.current)
  }

  async function handleTranscript(text) {
    setProcessing(true)
    setMatchResult(null)
    setSelectedProduct(null)
    try {
      const r = await fetch('/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: text }),
      })
      if (!r.ok) {
        const errText = await r.text()
        throw new Error(`Server error ${r.status}: ${errText.slice(0, 200)}`)
      }
      const data = await r.json()
      setMatchResult(data)
      // Pre-fill form with extracted values
      setForm({
        job: data.job || '',
        quantity: data.quantity != null ? String(data.quantity) : '',
        comments: data.comments || '',
      })
      // Auto-select if unambiguous single match
      if (!data.ambiguous && data.matches?.length === 1) {
        setSelectedProduct(data.matches[0])
      }
    } catch (e) {
      showToast('Error: ' + (e?.message || 'contacting server'))
      console.error('Match error:', e)
    }
    setProcessing(false)
  }

  // ── Submit ───────────────────────────────────────────────────────────────
  async function submitEntry() {
    if (!selectedProduct || !form.job || !form.quantity) return
    try {
      await fetch('/api/entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_code: selectedProduct.code,
          job: form.job,
          supplier: selectedProduct.supplier,
          description: selectedProduct.description,
          cost_quantity: parseFloat(form.quantity),
          unit: selectedProduct.unit,
          comments: form.comments,
        }),
      })
      showToast('Entry saved ✓')
      loadEntries()
      resetCapture()
    } catch {
      showToast('Save failed — try again')
    }
  }

  function resetCapture() {
    setTranscript('')
    setMatchResult(null)
    setSelectedProduct(null)
    setForm({ job: '', quantity: '', comments: '' })
  }

  async function deleteEntry(id) {
    await fetch(`/api/entries/${id}`, { method: 'DELETE' })
    loadEntries()
  }

  function showToast(msg) {
    setToast(msg)
    setToastShow(true)
    setTimeout(() => setToastShow(false), 2800)
  }

  const hasMatches = matchResult?.matches?.length > 0
  const isAmbiguous = matchResult?.ambiguous && matchResult?.matches?.length > 1
  const canSubmit = selectedProduct && form.job && form.quantity

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div style={S.app}>
      <style>{`
        @keyframes pulse {
          0%,100% { box-shadow: 0 0 0 12px rgba(224,82,82,0.15), 0 0 0 24px rgba(224,82,82,0.07); }
          50% { box-shadow: 0 0 0 18px rgba(224,82,82,0.2), 0 0 0 36px rgba(224,82,82,0.05); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        button:hover { opacity: .88; }
        input:focus { border-color: var(--accent) !important; }
      `}</style>

      {/* Header */}
      <header style={S.header}>
        <div>
          <div style={S.logo}>Sansom</div>
          <div style={S.logoSub}>Stock Book</div>
        </div>
        <div style={S.tabs}>
          {['capture','log'].map(t => (
            <button key={t} style={S.tab(tab===t)} onClick={() => setTab(t)}>
              {t === 'capture' ? '⬤ Capture' : '☰ Log'}
            </button>
          ))}
        </div>
      </header>

      <main style={S.main}>

        {/* ── CAPTURE TAB ─────────────────────────────────────────────── */}
        {tab === 'capture' && (
          <>
            <div style={S.voiceCard}>
              <div style={S.voiceTitle}>Voice Entry</div>
              <div style={S.voiceHint}>
                Hold the mic button and say the product name, job number, quantity and your name.<br/>
                <em style={{color:'var(--accent)'}}>e.g. "Sika Boom, job 2847, 3 cans, taken by Dave"</em>
              </div>

              <button
                style={S.micBtn(listening)}
                onMouseDown={startListening}
                onMouseUp={stopListening}
                onMouseLeave={listening ? stopListening : undefined}
                onTouchStart={(e) => { e.preventDefault(); startListening() }}
                onTouchEnd={(e) => { e.preventDefault(); stopListening() }}
              >
                {listening ? '⏹' : '🎤'}
              </button>

              <div style={{fontSize:13,color:listening?'var(--danger)':'var(--muted)',fontFamily:'var(--font-head)',letterSpacing:1}}>
                {listening ? 'LISTENING — RELEASE TO SUBMIT' : 'HOLD TO SPEAK'}
              </div>

              {transcript && (
                <div style={S.transcript}>
                  <span style={{color:'var(--muted)',fontSize:12,fontFamily:'var(--font-head)',letterSpacing:1}}>HEARD: </span>
                  {transcript}
                  <div style={{marginTop:6,fontSize:11,color:'var(--accent)',fontFamily:'var(--font-head)',letterSpacing:.5}}>
                    ↳ AI will translate & match automatically
                  </div>
                </div>
              )}
            </div>

            {/* Processing */}
            {processing && (
              <div style={S.processing}>
                <div style={S.spinner} />
                Matching product…
              </div>
            )}

            {/* Disambiguation */}
            {!processing && isAmbiguous && (
              <div style={S.disambigCard}>
                <div style={{...S.confirmTitle, color:'var(--text)', fontSize:15}}>
                  Multiple products found — which one?
                </div>
                {matchResult.matches.map(p => (
                  <div key={p.code}
                    style={S.productOption(selectedProduct?.code === p.code)}
                    onClick={() => setSelectedProduct(p)}>
                    <div style={S.productCode}>{p.code}</div>
                    <div>
                      <div style={S.productDesc}>{p.description}</div>
                      <div style={S.productSupplier}>{p.supplier} · <span style={{color:'var(--accent)'}}>{p.unit}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Confirm form */}
            {!processing && hasMatches && (
              <div style={S.confirmCard}>
                <div style={S.confirmTitle}>Confirm Entry</div>

                {/* Product display */}
                {selectedProduct && (
                  <div style={{...S.field, background:'var(--surface2)', borderRadius:8, padding:'12px 16px', marginBottom:20, border:'1px solid var(--border)'}}>
                    <span style={{...S.fieldLabel, marginBottom:2}}>Product</span>
                    <div style={{fontFamily:'var(--font-head)', fontSize:18, fontWeight:700, color:'var(--accent)'}}>{selectedProduct.code}</div>
                    <div style={{fontSize:14, color:'var(--text)', marginTop:2}}>{selectedProduct.description}</div>
                    <div style={{fontSize:12, color:'var(--muted)', marginTop:2}}>{selectedProduct.supplier}</div>
                  </div>
                )}

                <div style={S.row}>
                  <div style={S.field}>
                    <label style={S.fieldLabel}>Job Number *</label>
                    <input style={S.fieldInput} value={form.job}
                      onChange={e => setForm(f=>({...f, job: e.target.value}))}
                      placeholder="e.g. 2847" />
                  </div>
                  <div style={S.field}>
                    <label style={S.fieldLabel}>
                      Quantity *
                      {selectedProduct && <span style={S.unitHint}>unit: {selectedProduct.unit}</span>}
                    </label>
                    <input style={S.fieldInput} type="number" value={form.quantity}
                      onChange={e => setForm(f=>({...f, quantity: e.target.value}))}
                      placeholder="e.g. 4" />
                  </div>
                </div>

                <div style={S.field}>
                  <label style={S.fieldLabel}>Taken by (Comments)</label>
                  <input style={S.fieldInput} value={form.comments}
                    onChange={e => setForm(f=>({...f, comments: e.target.value}))}
                    placeholder="e.g. Dave" />
                </div>

                {/* Missing fields warning */}
                {matchResult?.missing?.length > 0 && (
                  <div style={{padding:'10px 14px', background:'rgba(224,82,82,.1)', border:'1px solid rgba(224,82,82,.3)', borderRadius:6, marginBottom:16, fontSize:13, color:'#f08080'}}>
                    ⚠ Not heard in transcript — please fill in: <strong>{matchResult.missing.join(', ')}</strong>
                  </div>
                )}

                <div style={S.btnRow}>
                  <button style={S.btnSecondary} onClick={resetCapture}>Cancel</button>
                  <button style={{...S.btnPrimary, opacity: canSubmit ? 1 : .4}} onClick={submitEntry} disabled={!canSubmit}>
                    Save Entry
                  </button>
                </div>
              </div>
            )}

            {/* No match */}
            {!processing && matchResult && !hasMatches && (
              <div style={{...S.confirmCard, border:'1px solid var(--danger)'}}>
                <div style={{color:'var(--danger)', fontFamily:'var(--font-head)', fontWeight:700, fontSize:16, marginBottom:8}}>
                  No product matched
                </div>
                <div style={{color:'var(--muted)', fontSize:14, marginBottom:16}}>
                  Try again with a different product name. You said: "{transcript}"
                </div>
                <button style={S.btnSecondary} onClick={resetCapture}>Try again</button>
              </div>
            )}
          </>
        )}

        {/* ── LOG TAB ─────────────────────────────────────────────────── */}
        {tab === 'log' && (
          <div style={S.logCard}>
            <div style={S.logHeader}>
              <div style={S.logTitle}>Stock Entries ({entries.length})</div>
              <a href="/api/export" download>
                <button style={S.exportBtn}>↓ Export CSV</button>
              </a>
            </div>

            {entries.length === 0 ? (
              <div style={S.empty}>No entries yet</div>
            ) : (
              <>
                <div style={{...S.logRow, borderBottom:'2px solid var(--border)'}}>
                  {['Item Code','Date','Job','Description','Qty',''].map((h,i)=>(
                    <div key={i} style={S.logHead}>{h}</div>
                  ))}
                </div>
                {entries.map(e => (
                  <div key={e.id} style={S.logRow}>
                    <div style={{fontFamily:'var(--font-head)',fontWeight:700,color:'var(--accent)',fontSize:13}}>{e.item_code}</div>
                    <div style={{color:'var(--muted)',fontSize:12}}>{String(e.entry_date).slice(0,10)}</div>
                    <div style={{fontFamily:'var(--font-head)',fontWeight:600}}>{e.job}</div>
                    <div style={{color:'var(--text)',fontSize:12,lineHeight:1.3}}>
                      {e.description}
                      {e.comments && <div style={{color:'var(--muted)',fontSize:11}}>{e.comments}</div>}
                    </div>
                    <div style={{fontFamily:'var(--font-head)',fontWeight:700}}>
                      {e.cost_quantity}<span style={{fontSize:10,color:'var(--muted)',marginLeft:2}}>{e.unit}</span>
                    </div>
                    <button style={S.deleteBtn} onClick={() => deleteEntry(e.id)} title="Delete">✕</button>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </main>

      {/* Toast */}
      <div style={S.toast(toastShow)}>{toast}</div>
    </div>
  )
}
