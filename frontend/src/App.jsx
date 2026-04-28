import React, { useState, useEffect, useRef } from 'react'

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
    padding: '0 16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 56,
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
  main: { flex: 1, maxWidth: 800, width: '100%', margin: '0 auto', padding: '24px 16px 100px' },
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

  // ── Log table ────────────────────────────────────────────────────────────
  logCard: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' },
  logHeader: { padding: '16px 20px', borderBottom: '1px solid var(--border)' },
  logTitleRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  logTitle: { fontFamily: 'var(--font-head)', fontSize: 16, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--muted)' },
  exportControls: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' },
  dateInput: {
    background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 4, padding: '6px 10px', color: 'var(--text)', fontSize: 13,
    fontFamily: 'var(--font-body)',
  },
  dateLabel: { fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--font-head)', letterSpacing: 1, textTransform: 'uppercase' },
  exportBtn: { padding: '7px 16px', background: 'var(--accent)', color: '#fff', fontFamily: 'var(--font-head)', fontSize: 13, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', borderRadius: 4, border: 'none', cursor: 'pointer' },

  // Updated log row: item_code | description | date | job | qty | worker | del
  logRow: { display: 'grid', gridTemplateColumns: '90px 1fr 80px 160px 55px 90px 36px 36px', gap: 8, padding: '12px 20px', borderBottom: '1px solid var(--border)', alignItems: 'center', fontSize: 13 },
  logHead: { fontFamily: 'var(--font-head)', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--muted)' },
  deleteBtn: { padding: '4px 8px', background: 'transparent', color: 'var(--danger)', fontSize: 16, borderRadius: 4, border: '1px solid transparent', cursor: 'pointer' },
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

  // ── Webhook / Settings tab ────────────────────────────────────────────────
  settingSection: { marginBottom: 28 },
  settingTitle: { fontFamily: 'var(--font-head)', fontSize: 14, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 12 },
  settingDesc: { fontSize: 13, color: 'var(--muted)', lineHeight: 1.7, marginBottom: 14 },
  codeBlock: {
    background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6,
    padding: '12px 16px', fontSize: 12, color: 'var(--accent)', fontFamily: 'monospace',
    overflowX: 'auto', whiteSpace: 'pre', marginBottom: 12,
  },
  statusBadge: (ok) => ({
    display: 'inline-block', padding: '3px 10px', borderRadius: 20,
    background: ok ? 'rgba(76,175,125,.15)' : 'rgba(224,82,82,.15)',
    color: ok ? 'var(--success)' : 'var(--danger)',
    fontFamily: 'var(--font-head)', fontSize: 12, fontWeight: 700, letterSpacing: 1,
  }),
  syncBtn: {
    padding: '10px 20px', background: 'var(--accent)', color: '#fff',
    fontFamily: 'var(--font-head)', fontSize: 13, fontWeight: 700,
    letterSpacing: 1, textTransform: 'uppercase', borderRadius: 6, border: 'none', cursor: 'pointer',
    marginTop: 12,
  },
  syncInput: {
    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 6, padding: '10px 14px', color: 'var(--text)', fontSize: 13,
    marginBottom: 10, fontFamily: 'var(--font-body)',
  },
}

export default function App() {
  const [tab, setTab] = useState('capture')
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [processing, setProcessing] = useState(false)
  const [matchResult, setMatchResult] = useState(null)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [form, setForm] = useState({ job: '', quantity: '', worker_name: '' })
  const [entries, setEntries] = useState([])
  const [toast, setToast] = useState('')
  const [toastShow, setToastShow] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  const [reportText, setReportText] = useState('')
  const [reportSending, setReportSending] = useState(false)
  const [reporterName, setReporterName] = useState(() => localStorage.getItem('reporterName') || '')
  const [inputMode, setInputMode] = useState('voice')
  const [textInput, setTextInput] = useState('')
  const [jobs, setJobs] = useState([])

  // Edit state
  const [editingEntry, setEditingEntry] = useState(null) // { id, job, cost_quantity, worker_name }
  const [editForm, setEditForm] = useState({})

  // Export date range state
  const [exportFrom, setExportFrom] = useState('')
  const [exportTo, setExportTo] = useState('')

  // Webhook / settings state
  const [webhookStatus, setWebhookStatus] = useState(null)
  const [syncProductsUrl, setSyncProductsUrl] = useState('')
  const [syncJobsUrl, setSyncJobsUrl] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [settingsUnlocked, setSettingsUnlocked] = useState(false)
  const [settingsPassword, setSettingsPassword] = useState('')
  const [settingsPasswordError, setSettingsPasswordError] = useState(false)

  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')

  useEffect(() => {
    loadEntries()
    fetch('/api/jobs').then(r => r.json()).then(setJobs).catch(() => {})
  }, [])

  useEffect(() => {
    if (tab === 'settings') loadWebhookStatus()
  }, [tab])

  async function loadEntries() {
    try {
      const r = await fetch('/api/entries')
      setEntries(await r.json())
    } catch {}
  }

  async function loadWebhookStatus() {
    try {
      const r = await fetch('/api/webhook/status')
      setWebhookStatus(await r.json())
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
        worker_name: data.worker_name || '',
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
          worker_name: form.worker_name,
        }),
      })
      showToast('Entry saved ✓')
      loadEntries()
      resetCapture()
    } catch { showToast('Save failed — try again') }
  }

  function resetCapture() {
    setTranscript(''); setTextInput(''); setMatchResult(null)
    setSelectedProduct(null); setForm({ job: '', quantity: '', worker_name: '' })
    setVoOptions([])
  }

  async function deleteEntry(id) {
    await fetch(`/api/entries/${id}`, { method: 'DELETE' })
    loadEntries()
  }

  async function saveEditEntry() {
    try {
      await fetch(`/api/entries/${editingEntry.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job: editForm.job,
          cost_quantity: parseFloat(editForm.cost_quantity),
          worker_name: editForm.worker_name,
        }),
      })
      showToast('Entry updated ✓')
      setEditingEntry(null)
      loadEntries()
    } catch { showToast('Update failed — try again') }
  }

  function showToast(msg) {
    setToast(msg); setToastShow(true)
    setTimeout(() => setToastShow(false), 2800)
  }

  async function submitReport() {
    if (!reportText.trim()) return
    setReportSending(true)
    if (reporterName.trim()) localStorage.setItem('reporterName', reporterName.trim())
    try {
      await fetch('https://hook.us2.make.com/k1vpgwnxstveou5913b9776b09gw3fnk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: reporterName.trim() || 'Unknown',
          issue: reportText.trim(),
          url: window.location.href,
          reported_at: new Date().toISOString(),
        }),
      })
      showToast('Issue reported — thank you ✓')
      setReportText('')
      setShowReportModal(false)
    } catch {
      showToast('Failed to send — please try again')
    }
    setReportSending(false)
  }

  function switchMode(mode) {
    setInputMode(mode); resetCapture()
  }

  function toISODate(val) {
    if (!val) return ''
    if (val.includes('/')) {
      const [d, m, y] = val.split('/')
      return `${y}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`
    }
    return val
  }

  function buildExportUrl() {
    const params = new URLSearchParams()
    if (exportFrom) params.set('date_from', toISODate(exportFrom))
    if (exportTo) params.set('date_to', toISODate(exportTo))
    const qs = params.toString()
    return `/api/export${qs ? '?' + qs : ''}`
  }

  async function triggerSync() {
    if (!syncProductsUrl && !syncJobsUrl) {
      showToast('Enter at least one URL to sync')
      return
    }
    setSyncing(true)
    try {
      const body = {}
      if (syncProductsUrl) body.products_csv_url = syncProductsUrl
      if (syncJobsUrl) body.jobs_csv_url = syncJobsUrl
      const r = await fetch('/api/webhook/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await r.json()
      if (data.ok) {
        showToast('Sync successful ✓')
        loadWebhookStatus()
        fetch('/api/jobs').then(r => r.json()).then(setJobs).catch(() => {})
      } else {
        showToast('Sync failed: ' + (data.message || 'unknown error'))
      }
    } catch (e) {
      showToast('Sync error: ' + (e?.message || 'network error'))
    }
    setSyncing(false)
  }

  const hasMatches = matchResult?.matches?.length > 0
  const isAmbiguous = matchResult?.ambiguous && matchResult?.matches?.length > 1
  const canSubmit = selectedProduct && form.job.trim() && form.quantity && form.worker_name.trim()


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
        input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(0.6); }
      `}</style>

      <div style={S.browserBanner}>
        🌐 Best on <strong>Chrome</strong> (Android, desktop). Safari on iPhone has limited mic support.
      </div>

      {/* ── GLOBAL RESPONSIVE STYLES ─────────────────────────────── */}
      <style>{`
        .logo-text { display: inline; }
        .desktop-tabs { display: flex; }
        .mobile-bottom-nav { display: none; }
        @media (max-width: 600px) {
          .logo-text { display: none; }
          .desktop-tabs { display: none !important; }
          .mobile-bottom-nav { display: flex !important; }
        }
      `}</style>

      <header style={S.header}>
        <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          <img src="/sansom-logo.jpg" alt="Sansom" style={{ height: 32, borderRadius: 4 }} />
          <span className="logo-text" style={S.logoSub}>Stock Book</span>
        </div>
        <div className="desktop-tabs" style={S.tabs}>
          {[['capture','⬤ Capture'],['log','☰ Log'],['qr','⊞ QR'],['settings','⚙ Settings']].map(([t,label]) => (
            <button key={t} style={S.tab(tab===t)} onClick={() => setTab(t)}>{label}</button>
          ))}
        </div>
        <button
          onClick={() => { setShowReportModal(true); setReportText('') }}
          style={{
            background: 'transparent', border: '1px solid #e55', color: '#e55',
            borderRadius: 6, padding: '6px 10px', fontFamily: 'var(--font-head)',
            fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase',
            cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
          }}
        >⚠ <span className="logo-text">Report Issue</span></button>
      </header>

      {/* ── MOBILE BOTTOM NAV ────────────────────────────────────────── */}
      <nav className="mobile-bottom-nav" style={{
        display: 'none', position: 'fixed', bottom: 0, left: 0, right: 0,
        background: 'var(--surface)', borderTop: '2px solid var(--accent)',
        zIndex: 200, padding: '8px 0 max(8px, env(safe-area-inset-bottom))',
      }}>
        {[
          ['capture', '⬤', 'Capture'],
          ['log', '☰', 'Log'],
          ['qr', '⊞', 'QR'],
          ['settings', '⚙', 'Settings'],
        ].map(([t, icon, label]) => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, background: 'none', border: 'none', cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
            padding: '4px 0',
            color: tab === t ? 'var(--accent)' : 'var(--muted)',
          }}>
            <span style={{ fontSize: 18, lineHeight: 1 }}>{icon}</span>
            <span style={{
              fontFamily: 'var(--font-head)', fontSize: 10, fontWeight: 700,
              letterSpacing: 1, textTransform: 'uppercase',
            }}>{label}</span>
          </button>
        ))}
      </nav>

      {/* ── REPORT ISSUE MODAL ───────────────────────────────────────── */}
      {showReportModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000, padding: 20,
        }} onClick={e => { if (e.target === e.currentTarget) setShowReportModal(false) }}>
          <div style={{
            background: 'var(--surface)', borderRadius: 12, padding: 28,
            width: '100%', maxWidth: 460, border: '1px solid var(--border)',
          }}>
            <div style={{ fontFamily: 'var(--font-head)', fontSize: 16, fontWeight: 800,
              letterSpacing: 2, textTransform: 'uppercase', color: 'var(--fg)', marginBottom: 6 }}>
              Report an Issue
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 18 }}>
              Describe what went wrong and we'll look into it.
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 11, fontFamily: 'var(--font-head)', letterSpacing: 1,
                color: 'var(--muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>
                Your Name
              </label>
              <input
                placeholder="e.g. John Smith"
                value={reporterName}
                onChange={e => setReporterName(e.target.value)}
                style={{
                  width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
                  borderRadius: 8, padding: '10px 12px', color: 'var(--fg)',
                  fontFamily: 'inherit', fontSize: 14, boxSizing: 'border-box',
                }}
              />
              {reporterName.trim() && (
                <div style={{ fontSize: 11, color: 'var(--accent)', marginTop: 4, fontFamily: 'var(--font-head)' }}>
                  ✓ Remembered on this device
                </div>
              )}
            </div>
            <textarea
              autoFocus
              placeholder="e.g. The microphone button isn't working, the product search returned wrong results..."
              value={reportText}
              onChange={e => setReportText(e.target.value)}
              rows={5}
              style={{
                width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '10px 12px', color: 'var(--fg)',
                fontFamily: 'inherit', fontSize: 14, resize: 'vertical', boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowReportModal(false)}
                style={{
                  background: 'transparent', border: '1px solid var(--border)',
                  color: 'var(--muted)', borderRadius: 6, padding: '8px 18px',
                  fontFamily: 'var(--font-head)', fontSize: 12, fontWeight: 700,
                  letterSpacing: 1, textTransform: 'uppercase', cursor: 'pointer',
                }}
              >Cancel</button>
              <button
                onClick={submitReport}
                disabled={!reportText.trim() || reportSending}
                style={{
                  background: reportText.trim() && !reportSending ? '#e55' : '#555',
                  border: 'none', color: '#fff', borderRadius: 6, padding: '8px 20px',
                  fontFamily: 'var(--font-head)', fontSize: 12, fontWeight: 700,
                  letterSpacing: 1, textTransform: 'uppercase',
                  cursor: reportText.trim() && !reportSending ? 'pointer' : 'default',
                  transition: 'background .15s',
                }}
              >{reportSending ? 'Sending…' : 'Send Report'}</button>
            </div>
          </div>
        </div>
      )}

      <main style={S.main}>

        {/* ── CAPTURE TAB ──────────────────────────────────────────── */}
        {tab === 'capture' && (
          <>
            <div style={S.card}>
              <div style={S.title}>New Entry</div>
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
                    <em style={{color:'var(--accent)'}}>e.g. "Sika Boom, job S34482, 3 cans, taken by Dave"</em>
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
                    <em style={{color:'var(--accent)'}}>e.g. "Sika Boom, job S34482, 3 cans, taken by Dave"</em>
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

            {processing && (
              <div style={S.processing}><div style={S.spinner} />Matching product…</div>
            )}

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

            {!processing && hasMatches && (
              <div style={S.cardAccent}>
                <div style={S.titleAccent}>Confirm Entry</div>

                {selectedProduct && (
                  <div style={{...S.field, background:'var(--surface2)', borderRadius:8, padding:'12px 16px', marginBottom:20, border:'1px solid var(--border)'}}>
                    <span style={{...S.fieldLabel, marginBottom:2}}>Product</span>
                    <div style={{fontFamily:'var(--font-head)', fontSize:18, fontWeight:700, color:'var(--accent)'}}>{selectedProduct.code}</div>
                    <div style={{fontSize:14, color:'var(--text)', marginTop:2}}>{selectedProduct.description}</div>
                    <div style={{fontSize:12, color:'var(--muted)', marginTop:2}}>{selectedProduct.supplier}</div>
                  </div>
                )}

                <div style={S.field}>
                  <label style={S.fieldLabel}>Job Number <span style={S.requiredStar}>*</span></label>
                  <select
                    style={S.fieldSelect}
                    value={form.job}
                    onChange={e => setForm(f => ({...f, job: e.target.value}))}
                  >
                    <option value="">— Select a job —</option>
                    {jobs.map(j => (
                      <option key={j} value={j}>{j}</option>
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
                    <label style={S.fieldLabel}>Worker Name <span style={S.requiredStar}>*</span></label>
                    <input
                      style={S.fieldInput}
                      value={form.worker_name}
                      onChange={e => setForm(f => ({...f, worker_name: e.target.value}))}
                      placeholder="e.g. Dave Smith"
                    />
                  </div>
                </div>

                {matchResult?.missing?.length > 0 && (
                  <div style={S.missingWarning}>
                    ⚠ Not found in transcript — please fill in: <strong>{matchResult.missing.join(', ')}</strong>
                  </div>
                )}

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
              <div style={S.logTitleRow}>
                <div style={S.logTitle}>Stock Entries ({entries.length})</div>
                <button style={S.exportBtn} onClick={() => {
                  const url = buildExportUrl()
                  window.open(url, '_blank')
                }}>↓ Export CSV</button>
              </div>

              {/* Date range filter for export */}
              <div style={S.exportControls}>
                <span style={S.dateLabel}>Export range:</span>
                <div style={{display:'flex', alignItems:'center', gap:6}}>
                  <span style={{fontSize:12, color:'var(--muted)'}}>From</span>
                  <input
                    type="date"
                    style={S.dateInput}
                    value={exportFrom}
                    onChange={e => setExportFrom(e.target.value)}
                  />
                </div>
                <div style={{display:'flex', alignItems:'center', gap:6}}>
                  <span style={{fontSize:12, color:'var(--muted)'}}>To</span>
                  <input
                    type="date"
                    style={S.dateInput}
                    value={exportTo}
                    onChange={e => setExportTo(e.target.value)}
                  />
                </div>
                {(exportFrom || exportTo) && (
                  <button
                    style={{...S.exportBtn, background:'transparent', color:'var(--muted)', border:'1px solid var(--border)'}}
                    onClick={() => { setExportFrom(''); setExportTo('') }}
                  >
                    Clear
                  </button>
                )}
              </div>
              {(exportFrom || exportTo) && (
                <div style={{fontSize:12, color:'var(--accent)', marginTop:8, fontFamily:'var(--font-head)', letterSpacing:.5}}>
                  ↑ Export CSV above will include only entries
                  {exportFrom ? ` from ${exportFrom}` : ''}
                  {exportTo ? ` to ${exportTo}` : ''}
                </div>
              )}
            </div>

            {entries.length === 0 ? (
              <div style={S.empty}>No entries yet</div>
            ) : (
              <>
                {/* Table header */}
                <div style={{...S.logRow, borderBottom:'2px solid var(--border)'}}>
                  {['Code','Product','Date','Job','Qty','Worker','',''].map((h,i) => (
                    <div key={i} style={S.logHead}>{h}</div>
                  ))}
                </div>
                {entries.map(e => (
                  <React.Fragment key={e.id}>
                    <div style={S.logRow}>
                      <div style={{fontFamily:'var(--font-head)',fontWeight:700,color:'var(--accent)',fontSize:12}}>{e.item_code}</div>
                      <div style={{color:'var(--text)',fontSize:12,lineHeight:1.3}}>{e.description}</div>
                      <div style={{color:'var(--muted)',fontSize:12}}>{String(e.entry_date).slice(0,10)}</div>
                      <div style={{color:'var(--text)',fontSize:12,lineHeight:1.3,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}} title={e.job}>
                        {e.job}
                      </div>
                      <div style={{fontFamily:'var(--font-head)',fontWeight:700,fontSize:13}}>
                        {e.cost_quantity}<span style={{fontSize:10,color:'var(--muted)',marginLeft:2}}>{e.unit}</span>
                      </div>
                      <div style={{color:'var(--muted)',fontSize:12,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}} title={e.worker_name}>
                        {e.worker_name || '—'}
                      </div>
                      <button
                        style={{padding:'4px 8px', background:'transparent', color:'var(--accent)', fontSize:14, borderRadius:4, border:'1px solid transparent', cursor:'pointer'}}
                        onClick={() => { setEditingEntry(e); setEditForm({ job: e.job, cost_quantity: e.cost_quantity, worker_name: e.worker_name || '' }) }}
                        title="Edit"
                      >✎</button>
                      <button style={S.deleteBtn} onClick={() => deleteEntry(e.id)} title="Delete">✕</button>
                    </div>
                    {editingEntry?.id === e.id && (
                      <div style={{gridColumn:'1/-1', background:'var(--surface2)', border:'1px solid var(--accent)', borderRadius:8, padding:'16px 20px', margin:'0 0 4px 0'}}>
                        <div style={{fontFamily:'var(--font-head)', fontSize:13, fontWeight:700, color:'var(--accent)', letterSpacing:1, marginBottom:12}}>EDITING: {e.item_code} — {e.description}</div>
                        <div style={{display:'grid', gridTemplateColumns:'1fr 100px 1fr', gap:12, marginBottom:12}}>
                          <div>
                            <label style={S.fieldLabel}>Job <span style={S.requiredStar}>*</span></label>
                            <select
                              style={{...S.fieldSelect, fontSize:13}}
                              value={editForm.job}
                              onChange={ev => setEditForm(f => ({...f, job: ev.target.value}))}
                            >
                              <option value="">— Select job —</option>
                              {jobs.map(j => <option key={j} value={j}>{j}</option>)}
                            </select>
                          </div>
                          <div>
                            <label style={S.fieldLabel}>Qty <span style={S.requiredStar}>*</span></label>
                            <input
                              type="number"
                              style={{...S.fieldInput, fontSize:13}}
                              value={editForm.cost_quantity}
                              onChange={ev => setEditForm(f => ({...f, cost_quantity: ev.target.value}))}
                            />
                          </div>
                          <div>
                            <label style={S.fieldLabel}>Worker <span style={S.requiredStar}>*</span></label>
                            <input
                              style={{...S.fieldInput, fontSize:13}}
                              value={editForm.worker_name}
                              onChange={ev => setEditForm(f => ({...f, worker_name: ev.target.value}))}
                            />
                          </div>
                        </div>
                        <div style={{display:'flex', gap:8}}>
                          <button style={{...S.btnPrimary(true), flex:'none', padding:'8px 20px', fontSize:13}} onClick={saveEditEntry}>Save</button>
                          <button style={{...S.btnSecondary, padding:'8px 16px', fontSize:13}} onClick={() => setEditingEntry(null)}>Cancel</button>
                        </div>
                      </div>
                    )}
                  </React.Fragment>
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
          </div>
        )}

        {/* ── SETTINGS TAB ─────────────────────────────────────────── */}
        {tab === 'settings' && (
          <div style={S.card}>
            <div style={S.title}>Settings & Sync</div>

            {!settingsUnlocked ? (
              <div style={{textAlign:'center', padding:'32px 0'}}>
                <div style={{color:'var(--muted)', fontSize:14, marginBottom:20, fontFamily:'var(--font-head)', letterSpacing:1, textTransform:'uppercase'}}>
                  Enter password to access settings
                </div>
                <input
                  type="password"
                  style={{...S.fieldInput, maxWidth:260, margin:'0 auto 12px', display:'block', textAlign:'center'}}
                  placeholder="Password"
                  value={settingsPassword}
                  onChange={e => { setSettingsPassword(e.target.value); setSettingsPasswordError(false) }}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      if (settingsPassword === 'Sansom12345') { setSettingsUnlocked(true); setSettingsPasswordError(false) }
                      else setSettingsPasswordError(true)
                    }
                  }}
                />
                {settingsPasswordError && (
                  <div style={{color:'var(--danger)', fontSize:13, marginBottom:12}}>Incorrect password</div>
                )}
                <button
                  style={{...S.syncBtn, marginTop:0}}
                  onClick={() => {
                    if (settingsPassword === 'Sansom12345') { setSettingsUnlocked(true); setSettingsPasswordError(false) }
                    else setSettingsPasswordError(true)
                  }}
                >Unlock</button>
              </div>
            ) : (<>

            {/* Status */}
            <div style={S.settingSection}>
              <div style={S.settingTitle}>Current Data Status</div>
              {webhookStatus ? (
                <div style={{display:'flex', gap:16, flexWrap:'wrap', marginBottom:12}}>
                  <div style={{background:'var(--surface2)', borderRadius:8, padding:'12px 18px', border:'1px solid var(--border)'}}>
                    <div style={{fontSize:11, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:4}}>PRODUCTS LOADED</div>
                    <div style={{fontFamily:'var(--font-head)', fontSize:24, fontWeight:800, color:'var(--accent)'}}>{webhookStatus.products_count}</div>
                  </div>
                  <div style={{background:'var(--surface2)', borderRadius:8, padding:'12px 18px', border:'1px solid var(--border)'}}>
                    <div style={{fontSize:11, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:4}}>JOBS LOADED</div>
                    <div style={{fontFamily:'var(--font-head)', fontSize:24, fontWeight:800, color:'var(--accent)'}}>{webhookStatus.jobs_count}</div>
                  </div>
                  <div style={{background:'var(--surface2)', borderRadius:8, padding:'12px 18px', border:'1px solid var(--border)', flex:1, minWidth:180}}>
                    <div style={{fontSize:11, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:6}}>SOURCE</div>
                    <span style={S.statusBadge(webhookStatus.source?.includes('live'))}>
                      {webhookStatus.source?.includes('live') ? '● Live Sync' : '● Default (hardcoded)'}
                    </span>
                  </div>
                </div>
              ) : (
                <div style={{color:'var(--muted)', fontSize:13}}>Loading status…</div>
              )}
            </div>

            {/* Manual sync */}
            <div style={S.settingSection}>
              <div style={S.settingTitle}>Sync from Google Sheets</div>
              <div style={S.settingDesc}>
                Paste the published CSV URLs from your Google Sheets. The app will pull the latest product list and job list instantly — no redeploy needed.<br/><br/>
                <strong style={{color:'var(--text)'}}>How to get the URL from Google Sheets:</strong><br/>
                File → Share → Publish to web → select the sheet → CSV → Copy link
              </div>
              <div style={S.field}>
                <label style={S.fieldLabel}>Products Sheet CSV URL</label>
                <input
                  style={S.syncInput}
                  placeholder="https://docs.google.com/spreadsheets/d/.../pub?output=csv"
                  value={syncProductsUrl}
                  onChange={e => setSyncProductsUrl(e.target.value)}
                />
              </div>
              <div style={S.field}>
                <label style={S.fieldLabel}>Jobs Sheet CSV URL</label>
                <input
                  style={S.syncInput}
                  placeholder="https://docs.google.com/spreadsheets/d/.../pub?output=csv&gid=..."
                  value={syncJobsUrl}
                  onChange={e => setSyncJobsUrl(e.target.value)}
                />
              </div>
              <button style={S.syncBtn} onClick={triggerSync} disabled={syncing}>
                {syncing ? '⏳ Syncing…' : '↻ Sync Now'}
              </button>
            </div>

            {/* API webhook docs */}
            <div style={S.settingSection}>
              <div style={S.settingTitle}>Automated Webhook (API)</div>
              <div style={S.settingDesc}>
                You can also POST to the sync endpoint directly from any automation tool (Zapier, Make, Google Apps Script, etc.) to keep the app updated automatically whenever your sheet changes.
              </div>
              <div style={{fontSize:12, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:6}}>ENDPOINT</div>
              <div style={S.codeBlock}>POST /api/webhook/sync</div>
              <div style={{fontSize:12, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:6}}>EXAMPLE PAYLOAD</div>
              <div style={S.codeBlock}>{`{
  "products_csv_url": "https://docs.google.com/...",
  "jobs_csv_url": "https://docs.google.com/..."
}`}</div>
              <div style={{fontSize:12, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:6}}>PRODUCTS CSV COLUMNS REQUIRED</div>
              <div style={S.codeBlock}>code, description, supplier, unit, gl, alias</div>
              <div style={{fontSize:12, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:6}}>JOBS CSV COLUMN REQUIRED</div>
              <div style={S.codeBlock}>job</div>
            </div>
            </>)}
          </div>
        )}

      </main>

      <div style={S.toast(toastShow)}>{toast}</div>
    </div>
  )
}
