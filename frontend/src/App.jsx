import { useState, useEffect, useRef } from 'react'

const S = {
  app: { minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' },
  browserBanner: {
    background: 'rgba(27,158,212,0.1)',
    borderBottom: '1px solid rgba(27,158,212,0.3)',
    padding: '8px 20px',
    textAlign: 'center',
    fontSize: 13,
    color: 'var(--muted)',
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
  logoSub: {
    fontFamily: 'var(--font-head)',
    fontSize: 13,
    color: 'var(--muted)',
    letterSpacing: 3,
    textTransform: 'uppercase',
    marginLeft: 10,
  },
  tabs: { display: 'flex', gap: 4 },
  tab: (active) => ({
    padding: '8px 16px',
    background: active ? 'var(--accent)' : 'transparent',
    color: active ? '#fff' : 'var(--muted)',
    fontFamily: 'var(--font-head)',
    fontWeight: 700,
    fontSize: 14,
    letterSpacing: 1,
    textTransform: 'uppercase',
    border: active ? 'none' : '1px solid var(--border)',
    borderRadius: 4,
    transition: 'all .15s',
  }),
  main: { flex: 1, maxWidth: 700, width: '100%', margin: '0 auto', padding: '32px 20px' },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: 28,
    marginBottom: 24,
  },
  cardAccent: {
    background: 'var(--surface)',
    border: '1px solid var(--accent)',
    borderRadius: 12,
    padding: 28,
    marginBottom: 24,
  },
  title: {
    fontFamily: 'var(--font-head)',
    fontSize: 20,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: 'var(--text)',
    marginBottom: 6,
  },
  titleAccent: {
    fontFamily: 'var(--font-head)',
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: 'var(--accent)',
    marginBottom: 20,
  },
  hint: { color: 'var(--muted)', fontSize: 14, marginBottom: 24, lineHeight: 1.6 },
  micBtn: (listening) => ({
    width: 96, height: 96, borderRadius: '50%',
    background: listening ? 'var(--danger)' : 'var(--accent)',
    color: '#fff', fontSize: 36,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    margin: '0 auto 20px',
    transition: 'all .2s',
    boxShadow: listening
      ? '0 0 0 12px rgba(224,82,82,0.15), 0 0 0 24px rgba(224,82,82,0.07)'
      : '0 4px 20px rgba(27,158,212,0.4)',
    animation: listening ? 'pulse 1.4s ease-in-out infinite' : 'none',
  }),
  transcript: {
    background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 8, padding: '14px 18px', marginTop: 16,
    color: 'var(--text)', fontSize: 15, lineHeight: 1.6, minHeight: 52, textAlign: 'left',
  },
  fieldLabel: {
    fontSize: 11, fontFamily: 'var(--font-head)', fontWeight: 600,
    letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--muted)',
    marginBottom: 4, display: 'block',
  },
  fieldInput: {
    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 6, padding: '10px 14px', color: 'var(--text)', fontSize: 15,
    transition: 'border-color .15s',
  },
  fieldSelect: {
    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 6, padding: '10px 14px', color: 'var(--text)', fontSize: 15,
    transition: 'border-color .15s', appearance: 'none',
  },
  unitHint: {
    display: 'inline-block', marginLeft: 10, fontSize: 12,
    color: 'var(--accent)', fontFamily: 'var(--font-head)', fontWeight: 600, letterSpacing: .5,
  },
  row: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 },
  field: { marginBottom: 14 },
  btnRow: { display: 'flex', gap: 10, marginTop: 20 },
  btnPrimary: (enabled) => ({
    flex: 1, padding: '13px 0',
    background: 'var(--accent)', color: '#fff',
    fontFamily: 'var(--font-head)', fontSize: 16, fontWeight: 800,
    letterSpacing: 1.5, textTransform: 'uppercase', borderRadius: 6,
    opacity: enabled ? 1 : 0.4, transition: 'opacity .15s',
  }),
  btnSecondary: {
    padding: '13px 22px', background: 'transparent', color: 'var(--muted)',
    fontFamily: 'var(--font-head)', fontSize: 15, fontWeight: 700,
    letterSpacing: 1, textTransform: 'uppercase', borderRadius: 6,
    border: '1px solid var(--border)',
  },
  btnSubmitRow: { display: 'flex', gap: 10, marginTop: 14, justifyContent: 'center' },
  productOption: (selected) => ({
    display: 'flex', alignItems: 'center', gap: 14,
    padding: '14px 16px',
    background: selected ? 'rgba(27,158,212,.08)' : 'var(--surface2)',
    border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
    borderRadius: 8, marginBottom: 10, cursor: 'pointer', transition: 'all .15s',
  }),
  productCode: { fontFamily: 'var(--font-head)', fontSize: 20, fontWeight: 700, color: 'var(--accent)', minWidth: 100 },
  productDesc: { fontSize: 14, color: 'var(--text)', lineHeight: 1.4 },
  productSupplier: { fontSize: 12, color: 'var(--muted)', marginTop: 2 },
  logCard: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' },
  logHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border)' },
  logTitle: { fontFamily: 'var(--font-head)', fontSize: 16, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--muted)' },
  exportBtn: { padding: '7px 16px', background: 'var(--accent)', color: '#fff', fontFamily: 'var(--font-head)', fontSize: 13, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', borderRadius: 4 },
  logRow: { display: 'grid', gridTemplateColumns: '100px 85px 1fr 60px 50px', gap: 10, padding: '12px 20px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 },
  logHead: { fontFamily: 'var(--font-head)', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--muted)' },
  deleteBtn: { padding: '4px 8px', background: 'transparent', color: 'var(--danger)', fontSize: 16, borderRadius: 4, border: '1px solid transparent' },
  empty: { padding: '40px 20px', textAlign: 'center', color: 'var(--muted)', fontFamily: 'var(--font-head)', fontSize: 16, letterSpacing: 1, textTransform: 'uppercase' },
  toast: (show) => ({
    position: 'fixed', bottom: 32, left: '50%',
    transform: `translateX(-50%) translateY(${show ? 0 : 80}px)`,
    opacity: show ? 1 : 0,
    background: 'var(--success)', color: '#fff',
    padding: '12px 28px', borderRadius: 8,
    fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 15, letterSpacing: 1, textTransform: 'uppercase',
    transition: 'all .3s', zIndex: 999, pointerEvents: 'none',
  }),
  processing: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '20px 0', color: 'var(--muted)', fontFamily: 'var(--font-head)', letterSpacing: 1, textTransform: 'uppercase', fontSize: 14 },
  spinner: { width: 20, height: 20, border: '2px solid var(--border)', borderTop: '2px solid var(--accent)', borderRadius: '50%', animation: 'spin .7s linear infinite' },
  modeToggle: { display: 'flex', gap: 0, marginBottom: 24, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)', width: 'fit-content', margin: '0 auto 24px' },
  modeBtn: (active) => ({
    padding: '9px 24px',
    background: active ? 'var(--accent)' : 'transparent',
    color: active ? '#fff' : 'var(--muted)',
    fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 14,
    letterSpacing: 1, textTransform: 'uppercase', border: 'none', transition: 'all .15s',
  }),
  requiredStar: { color: 'var(--danger)', marginLeft: 3 },
  missingWarning: {
    padding: '10px 14px', background: 'rgba(224,82,82,.1)',
    border: '1px solid rgba(224,82,82,.3)', borderRadius: 6,
    marginBottom: 16, fontSize: 13, color: '#f08080',
  },
}

export default function App() {
  const [tab, setTab] = useState('capture')
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [processing, setProcessing] = useState(false)
  const [matchResult, setMatchResult] = useState(null)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [form, setForm] = useState({ job: '', quantity: '', comments: '' })
  const [entries, setEntries] = useState([])
  const [toast, setToast] = useState('')
  const [toastShow, setToastShow] = useState(false)
  const [inputMode, setInputMode] = useState('voice')
  const [textInput, setTextInput] = useState('')
  const [jobs, setJobs] = useState([])
  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')

  useEffect(() => {
    loadEntries()
    fetch('/api/jobs').then(r => r.json()).then(setJobs).catch(() => {})
  }, [])

  async function loadEntries() {
    try {
      const r = await fetch('/api/entries')
      setEntries(await r.json())
    } catch {}
  }

  // ── Voice ─────────────────────────────────────────────────────────────────
  function toggleListening() {
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      return
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      alert('Speech recognition not supported.\nPlease use Safari on iPhone, or Chrome on Android/desktop.')
      return
    }
    const rec = new SR()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'en-NZ'
    recognitionRef.current = rec
    transcriptRef.current = ''
    setTranscript('')

    rec.onstart = () => setListening(true)
    rec.onresult = (e) => {
      const t = Array.from(e.results).map(r => r[0].transcript).join('')
      transcriptRef.current = t
      setTranscript(t)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    rec.start()
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
      if (!r.ok) throw new Error(`Server error ${r.status}: ${(await r.text()).slice(0, 200)}`)
      const data = await r.json()
      setMatchResult(data)
      setForm({
        job: data.job || '',
        quantity: data.quantity != null ? String(data.quantity) : '',
        comments: data.comments || '',
      })
      if (!data.ambiguous && data.matches?.length === 1) setSelectedProduct(data.matches[0])
    } catch (e) {
      showToast('Error: ' + (e?.message || 'contacting server'))
    }
    setProcessing(false)
  }

  async function submitEntry() {
    if (!canSubmit) return
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
          gl_code: selectedProduct.gl || '',
          comments: form.comments,
        }),
      })
      showToast('Entry saved ✓')
      loadEntries()
      resetCapture()
    } catch { showToast('Save failed — try again') }
  }

  function resetCapture() {
    setTranscript(''); setTextInput(''); setMatchResult(null)
    setSelectedProduct(null); setForm({ job: '', quantity: '', comments: '' })
  }

  async function deleteEntry(id) {
    await fetch(`/api/entries/${id}`, { method: 'DELETE' })
    loadEntries()
  }

  function showToast(msg) {
    setToast(msg); setToastShow(true)
    setTimeout(() => setToastShow(false), 2800)
  }

  function switchMode(mode) {
    setInputMode(mode); resetCapture()
  }

  const hasMatches = matchResult?.matches?.length > 0
  const isAmbiguous = matchResult?.ambiguous && matchResult?.matches?.length > 1
  // All fields mandatory
  const canSubmit = selectedProduct && form.job.trim() && form.quantity && form.comments.trim()

  return (
    <div style={S.app}>
      <style>{`
        @keyframes pulse {
          0%,100% { box-shadow: 0 0 0 12px rgba(224,82,82,0.15), 0 0 0 24px rgba(224,82,82,0.07); }
          50% { box-shadow: 0 0 0 18px rgba(224,82,82,0.2), 0 0 0 36px rgba(224,82,82,0.05); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        button:hover { opacity: .88; }
        input:focus, textarea:focus, select:focus { border-color: var(--accent) !important; }
        select option { background: #182030; color: #e8ecf2; }
      `}</style>

      {/* Browser notice */}
      <div style={S.browserBanner}>
        🌐 For best results use <strong>Safari on iPhone</strong> or <strong>Chrome on Android / desktop</strong>
      </div>

      {/* Header */}
      <header style={S.header}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img src="/sansom-logo.jpg" alt="Sansom" style={{ height: 36, borderRadius: 4 }} />
          <span style={S.logoSub}>Stock Book</span>
        </div>
        <div style={S.tabs}>
          {[['capture','⬤ Capture'],['log','☰ Log'],['qr','⊞ QR']].map(([t,label]) => (
            <button key={t} style={S.tab(tab===t)} onClick={() => setTab(t)}>{label}</button>
          ))}
        </div>
      </header>

      <main style={S.main}>

        {/* ── CAPTURE TAB ──────────────────────────────────────────── */}
        {tab === 'capture' && (
          <>
            <div style={S.card}>
              <div style={S.title}>New Entry</div>

              {/* Mode toggle */}
              <div style={S.modeToggle}>
                {[['voice','🎤 Voice'],['text','⌨️ Type']].map(([mode,label]) => (
                  <button key={mode} style={S.modeBtn(inputMode===mode)} onClick={() => switchMode(mode)}>
                    {label}
                  </button>
                ))}
              </div>

              {inputMode === 'voice' ? (
                <>
                  <div style={S.hint}>
                    Tap the mic and say the product name, job number, quantity and your name.<br/>
                    <em style={{color:'var(--accent)'}}>e.g. "Sika Boom, job 2847, 3 cans, taken by Dave"</em>
                  </div>
                  <button style={S.micBtn(listening)} onClick={toggleListening}>
                    {listening ? '⏹' : '🎤'}
                  </button>
                  <div style={{fontSize:13, color:listening?'var(--danger)':'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, textAlign:'center'}}>
                    {listening ? 'LISTENING — TAP TO STOP' : 'TAP TO SPEAK'}
                  </div>
                  {transcript && (
                    <div style={S.transcript}>
                      <span style={{color:'var(--muted)',fontSize:12,fontFamily:'var(--font-head)',letterSpacing:1}}>HEARD: </span>
                      {transcript}
                    </div>
                  )}
                  {transcript && !listening && (
                    <div style={S.btnSubmitRow}>
                      <button style={{...S.btnSecondary, padding:'10px 20px'}} onClick={resetCapture}>Clear</button>
                      <button style={{...S.btnPrimary(true), flex:'none', padding:'10px 28px'}} onClick={() => handleTranscript(transcript)}>Submit ✓</button>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div style={S.hint}>
                    Type the product name, job number, quantity and your name.<br/>
                    <em style={{color:'var(--accent)'}}>e.g. "Sika Boom, job 2847, 3 cans, taken by Dave"</em>
                  </div>
                  <textarea
                    value={textInput}
                    onChange={e => setTextInput(e.target.value)}
                    placeholder='e.g. "Sika Boom, job S34482, 3 cans, taken by Dave"'
                    style={{...S.fieldInput, minHeight:90, resize:'vertical', marginBottom:14}}
                  />
                  <div style={S.btnSubmitRow}>
                    <button style={{...S.btnSecondary, padding:'10px 20px'}} onClick={resetCapture}>Clear</button>
                    <button
                      style={{...S.btnPrimary(!!textInput.trim()), flex:'none', padding:'10px 28px'}}
                      onClick={() => { if(textInput.trim()) handleTranscript(textInput) }}
                      disabled={!textInput.trim()}
                    >Submit ✓</button>
                  </div>
                </>
              )}
            </div>

            {/* Processing */}
            {processing && (
              <div style={S.processing}><div style={S.spinner} />Matching product…</div>
            )}

            {/* Disambiguation */}
            {!processing && isAmbiguous && (
              <div style={S.card}>
                <div style={{...S.titleAccent, color:'var(--text)', fontSize:15}}>
                  Multiple products found — which one?
                </div>
                {matchResult.matches.map(p => (
                  <div key={p.code} style={S.productOption(selectedProduct?.code === p.code)} onClick={() => setSelectedProduct(p)}>
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
              <div style={S.cardAccent}>
                <div style={S.titleAccent}>Confirm Entry</div>

                {/* Product display */}
                {selectedProduct && (
                  <div style={{...S.field, background:'var(--surface2)', borderRadius:8, padding:'12px 16px', marginBottom:20, border:'1px solid var(--border)'}}>
                    <span style={{...S.fieldLabel, marginBottom:2}}>Product</span>
                    <div style={{fontFamily:'var(--font-head)', fontSize:18, fontWeight:700, color:'var(--accent)'}}>{selectedProduct.code}</div>
                    <div style={{fontSize:14, color:'var(--text)', marginTop:2}}>{selectedProduct.description}</div>
                    <div style={{fontSize:12, color:'var(--muted)', marginTop:2}}>{selectedProduct.supplier}</div>
                  </div>
                )}

                {/* Job dropdown */}
                <div style={S.field}>
                  <label style={S.fieldLabel}>Job Number <span style={S.requiredStar}>*</span></label>
                  <select
                    style={S.fieldSelect}
                    value={form.job}
                    onChange={e => setForm(f => ({...f, job: e.target.value}))}
                  >
                    <option value="">— Select a job —</option>
                    {jobs.map(j => (
                      <option key={j} value={j} selected={form.job === j}>{j}</option>
                    ))}
                  </select>
                  {form.job && (
                    <div style={{fontSize:12, color:'var(--accent)', marginTop:4, fontFamily:'var(--font-head)'}}>
                      ✓ {form.job}
                    </div>
                  )}
                </div>

                <div style={S.row}>
                  <div style={S.field}>
                    <label style={S.fieldLabel}>
                      Quantity <span style={S.requiredStar}>*</span>
                      {selectedProduct && <span style={S.unitHint}>unit: {selectedProduct.unit}</span>}
                    </label>
                    <input
                      style={S.fieldInput}
                      type="number"
                      value={form.quantity}
                      onChange={e => setForm(f => ({...f, quantity: e.target.value}))}
                      placeholder="e.g. 4"
                    />
                  </div>
                  <div style={S.field}>
                    <label style={S.fieldLabel}>Taken by <span style={S.requiredStar}>*</span></label>
                    <input
                      style={S.fieldInput}
                      value={form.comments}
                      onChange={e => setForm(f => ({...f, comments: e.target.value}))}
                      placeholder="e.g. Dave"
                    />
                  </div>
                </div>

                {/* Missing fields warning */}
                {matchResult?.missing?.length > 0 && (
                  <div style={S.missingWarning}>
                    ⚠ Not found in transcript — please fill in: <strong>{matchResult.missing.join(', ')}</strong>
                  </div>
                )}

                {/* Mandatory fields reminder */}
                {!canSubmit && (
                  <div style={{...S.missingWarning, background:'rgba(27,158,212,.08)', border:'1px solid rgba(27,158,212,.3)', color:'var(--muted)'}}>
                    All fields marked <span style={{color:'var(--danger)'}}>*</span> are required before saving
                  </div>
                )}

                <div style={S.btnRow}>
                  <button style={S.btnSecondary} onClick={resetCapture}>Cancel</button>
                  <button style={S.btnPrimary(canSubmit)} onClick={submitEntry} disabled={!canSubmit}>
                    Save Entry
                  </button>
                </div>
              </div>
            )}

            {/* No match */}
            {!processing && matchResult && !hasMatches && (
              <div style={{...S.card, border:'1px solid var(--danger)'}}>
                <div style={{color:'var(--danger)', fontFamily:'var(--font-head)', fontWeight:700, fontSize:16, marginBottom:8}}>No product matched</div>
                <div style={{color:'var(--muted)', fontSize:14, marginBottom:16}}>
                  Try again with a different product name or description.
                </div>
                <button style={S.btnSecondary} onClick={resetCapture}>Try again</button>
              </div>
            )}
          </>
        )}

        {/* ── LOG TAB ──────────────────────────────────────────────── */}
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
                  {['Item Code','Date','Job','Qty',''].map((h,i) => (
                    <div key={i} style={S.logHead}>{h}</div>
                  ))}
                </div>
                {entries.map(e => (
                  <div key={e.id} style={S.logRow}>
                    <div style={{fontFamily:'var(--font-head)',fontWeight:700,color:'var(--accent)',fontSize:13}}>{e.item_code}</div>
                    <div style={{color:'var(--muted)',fontSize:12}}>{String(e.entry_date).slice(0,10)}</div>
                    <div style={{color:'var(--text)',fontSize:12,lineHeight:1.3}}>
                      {e.job}
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

        {/* ── QR TAB ───────────────────────────────────────────────── */}
        {tab === 'qr' && (
          <div style={{maxWidth:480, margin:'0 auto', width:'100%'}}>
            <div style={{textAlign:'right', marginBottom:16}} className="no-print">
              <button style={{...S.exportBtn, cursor:'pointer'}} onClick={() => window.print()}>
                🖨 Print This Page
              </button>
            </div>
            <div style={{background:'#fff', borderRadius:12, padding:36, textAlign:'center', border:'1px solid var(--border)', color:'#111'}}>
              <img src="/sansom-logo.jpg" alt="Sansom" style={{height:52, marginBottom:20}} />
              <div style={{fontFamily:'var(--font-head)', fontSize:22, fontWeight:800, letterSpacing:2, textTransform:'uppercase', color:'#111', marginBottom:12}}>
                Stock Book Entry
              </div>
              <div style={{fontSize:14, color:'#444', lineHeight:1.8, marginBottom:28, maxWidth:340, margin:'0 auto 28px'}}>
                Scan this QR code when you take stock.<br/>
                Press the microphone button and say the <strong>product name</strong>, <strong>how many units</strong>, <strong>job name and number</strong>, and <strong>your name</strong>.
              </div>
              <div style={{background:'#fff', padding:12, display:'inline-block', borderRadius:8, border:'1px solid #ddd', marginBottom:20}}>
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(window.location.origin)}`}
                  alt="QR Code"
                  style={{display:'block', width:220, height:220}}
                />
              </div>
              <div style={{fontSize:12, color:'#888', marginBottom:4}}>Scan to open the Stock Book app</div>
              <div style={{fontSize:11, color:'#bbb', wordBreak:'break-all'}}>{window.location.origin}</div>
            </div>
            <style>{`
              @media print {
                .no-print { display: none !important; }
                body { background: white !important; }
                header { display: none !important; }
              }
            `}</style>
          </div>
        )}

      </main>

      <div style={S.toast(toastShow)}>{toast}</div>
    </div>
  )
}
