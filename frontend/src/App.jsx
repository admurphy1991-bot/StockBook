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
  jobComboWrap: { position: 'relative' },
  jobComboInput: {
    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 6, padding: '10px 14px', color: 'var(--text)', fontSize: 15,
    transition: 'border-color .15s', boxSizing: 'border-box',
  },
  jobDropdown: {
    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 500,
    background: 'var(--surface)', border: '1px solid var(--accent)',
    borderTop: 'none', borderRadius: '0 0 8px 8px',
    maxHeight: 240, overflowY: 'auto',
    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
  },
  jobDropItem: (highlighted) => ({
    padding: '10px 14px', cursor: 'pointer', fontSize: 14,
    color: highlighted ? '#fff' : 'var(--text)',
    background: highlighted ? 'var(--accent)' : 'transparent',
    borderBottom: '1px solid var(--border)',
    lineHeight: 1.35,
  }),
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

  // ── Day Works ────────────────────────────────────────────────────────────
  dwToggle: { display: 'flex', gap: 0, marginBottom: 20, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)', width: 'fit-content' },
  dwToggleBtn: (active) => ({
    padding: '8px 22px', background: active ? 'var(--accent)' : 'transparent',
    color: active ? '#fff' : 'var(--muted)', border: 'none',
    fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 13, letterSpacing: 1,
    textTransform: 'uppercase', cursor: 'pointer', transition: 'all .15s',
  }),
  dwProgressTrack: { height: 3, background: 'var(--surface2)', borderRadius: 2, overflow: 'hidden' },
  dwProgressFill: (pct) => ({ height: '100%', background: 'var(--accent)', borderRadius: 2, width: `${pct}%`, transition: 'width .2s' }),
  dwTabRow: { display: 'flex', gap: 2, marginTop: 10, overflowX: 'auto' },
  dwTabBtn: (active) => ({
    flex: 'none', display: 'flex', alignItems: 'center', gap: 6, border: 'none', background: 'none',
    fontFamily: 'var(--font-head)', fontSize: 12.5, letterSpacing: .5, textTransform: 'uppercase',
    padding: '8px 10px', borderRadius: '6px 6px 0 0', cursor: 'pointer',
    color: active ? 'var(--accent)' : 'var(--muted)', fontWeight: 700,
    borderBottom: `2px solid ${active ? 'var(--accent)' : 'transparent'}`,
  }),
  dwTabBadge: (done, active) => ({
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 18, height: 18,
    borderRadius: '50%', fontSize: 10.5, fontWeight: 700,
    background: done ? 'var(--accent)' : (active ? 'transparent' : 'var(--surface2)'),
    color: done ? '#fff' : (active ? 'var(--accent)' : 'var(--muted)'),
    border: !done && active ? '1.5px solid var(--accent)' : 'none',
  }),
  dwCaptureWrap: { padding: '14px 16px', background: 'var(--surface)', borderBottom: '1px solid var(--border)' },
  dwMicBtn: (listening) => ({
    width: 72, height: 72, borderRadius: '50%', border: 'none', cursor: 'pointer', fontSize: 28,
    background: listening ? 'var(--danger)' : 'var(--accent)', color: '#fff',
    animation: listening ? 'pulse 1.4s ease-in-out infinite' : 'none',
  }),
  dwCaptureDisplay: { width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 14px', minHeight: 24, fontSize: 13.5, color: 'var(--text)', lineHeight: 1.5 },
  dwCaptureBar: { display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 10px' },
  dwLastParsed: { marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, fontSize: 12.5, color: 'var(--accent)', background: 'rgba(27,158,212,.1)', border: '1px solid rgba(27,158,212,.3)', borderRadius: 7, padding: '8px 10px' },
  dwSection: { background: 'var(--surface)', margin: '14px 14px 0', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' },
  dwSectionPad: { background: 'var(--surface)', margin: '14px 14px 0', border: '1px solid var(--border)', borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', gap: 14 },
  dwSectionHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 16px', borderBottom: '1px solid var(--border)' },
  dwSectionTitle: { fontFamily: 'var(--font-head)', fontSize: 15, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--muted)' },
  dwRow: { padding: '14px 16px', borderBottom: '1px solid var(--surface2)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 },
  dwRowEmpty: { padding: '22px 16px', textAlign: 'center', fontSize: 13, color: 'var(--muted)' },
  dwFieldWrap: { display: 'flex', flexDirection: 'column', gap: 6 },
  dwYesNo: { display: 'flex', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' },
  dwYesNoBtn: (active, first) => ({
    flex: 1, border: 'none', padding: 11, fontFamily: 'var(--font-head)', fontSize: 14, fontWeight: 700,
    letterSpacing: .5, textTransform: 'uppercase', cursor: 'pointer',
    background: active ? 'var(--accent)' : 'var(--surface2)', color: active ? '#fff' : 'var(--muted)',
    borderRight: first && !active ? '1px solid var(--border)' : 'none',
  }),
  dwCompleteWrap: { padding: '48px 24px', display: 'flex', flexDirection: 'column', gap: 14, alignItems: 'center', textAlign: 'center' },
  dwCheckCircle: { width: 64, height: 64, borderRadius: '50%', background: 'rgba(76,175,125,.12)', border: '1px solid var(--success)', color: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30 },
  dwWebhookNote: { marginTop: 2, display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(27,158,212,.1)', border: '1px solid rgba(27,158,212,.3)', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: 'var(--muted)' },
  dwLogCard: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 14, marginBottom: 10 },
  dwStatusBadge: (color) => ({ fontFamily: 'var(--font-head)', fontSize: 11, fontWeight: 700, letterSpacing: .5, textTransform: 'uppercase', padding: '4px 10px', borderRadius: 20, background: color + '26', color }),
  dwPdfPage: { background: '#eef1f5', minHeight: 400, padding: 18, borderRadius: 8, color: '#1a1f27' },
  dwPdfSheet: { background: '#fff', borderRadius: 6, padding: '22px 20px', fontFamily: 'Arial,Helvetica,sans-serif', color: '#1a1f27', boxShadow: '0 2px 10px rgba(0,0,0,.08)' },
  dwPdfTh: { border: '1px solid #ccc', padding: 5, textAlign: 'left', background: '#f3f4f6' },
  dwPdfTd: { border: '1px solid #ccc', padding: 5 },
}


// ── Day Works helpers ─────────────────────────────────────────────────────────
const DW_TABS = [
  { id: 'details', label: 'Details' },
  { id: 'labour', label: 'Labour' },
  { id: 'materials', label: 'Materials' },
  { id: 'comments', label: 'Comments' },
  { id: 'signoff', label: 'Sign-off' },
]
const DW_UNIT_WORDS = ['bags', 'bag', 'metres', 'meters', 'm', 'kg', 'tonnes', 'tonne', 'boxes', 'box', 'units', 'unit', 'litres', 'litre', 'l', 'pieces', 'piece', 'sheets', 'sheet', 'rolls', 'roll']

function dwTodayISO() {
  return new Date().toISOString().slice(0, 10)
}

function dwParseTimeToMinutes(raw) {
  const m = raw.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i)
  if (!m) return null
  let h = parseInt(m[1], 10)
  const min = m[2] ? parseInt(m[2], 10) : 0
  const mer = m[3].toLowerCase()
  if (mer === 'pm' && h !== 12) h += 12
  if (mer === 'am' && h === 12) h = 0
  return h * 60 + min
}

function dwFormatMinutes(mins) {
  let h = Math.floor(mins / 60)
  const mm = mins % 60
  const mer = h >= 12 ? 'pm' : 'am'
  let h12 = h % 12; if (h12 === 0) h12 = 12
  return mm ? `${h12}:${String(mm).padStart(2, '0')}${mer}` : `${h12}${mer}`
}

const DW_FRESH_FORM = {
  dwJob: '', dwDate: dwTodayISO(), dwVariation: '', dwVoNumber: '', dwLocation: '',
  dwLabourRows: [], dwMaterialRows: [], dwComments: '', dwPhotos: [],
  dwCaptureText: '', dwLastParsed: null, dwSignoffMode: 'glass', dwClientName: '', dwClientEmail: '',
  dwSigned: false, dwValidationMsg: '', dwActiveTab: 'details', dwInputMode: 'voice',
}

export default function App() {
  const [tab, setTab] = useState('capture')
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [processing, setProcessing] = useState(false)
  const [matchResult, setMatchResult] = useState(null)
  const [confirmedProducts, setConfirmedProducts] = useState([]) // [{...product, quantity:''}]
  const [form, setForm] = useState({ job: '', worker_name: '' })
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
  const [products, setProducts] = useState([])
  const [vos, setVos] = useState([])

  // Reference tab state
  const [refTab, setRefTab] = useState('tools') // 'tools' | 'products'
  const [refSearch, setRefSearch] = useState('')

  // Edit state
  const [editingEntry, setEditingEntry] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [editingToolEntry, setEditingToolEntry] = useState(null)
  const [editToolForm, setEditToolForm] = useState({})

  // Multi-entry basket
  const [basket, setBasket] = useState([]) // [{type:'stock'|'tool', product?, toolName?, quantity?}]
  const [basketJob, setBasketJob] = useState('')
  const [basketWorker, setBasketWorker] = useState('')

  // Log sub-tab
  const [logTab, setLogTab] = useState('stock') // 'stock' | 'tools'
  const [toolEntries, setToolEntries] = useState([])

  const [handTools, setHandTools] = useState([]) // {name, cost}[]

  // ── Room Lock ────────────────────────────────────────────────────
  const [roomLocked, setRoomLocked] = useState(() => localStorage.getItem('sb_locked') === 'true')
  const [awaySince, setAwaySince] = useState(() => { const v = localStorage.getItem('sb_since'); return v ? parseInt(v) : null })
  const [lockAlerts, setLockAlerts] = useState(() => { try { return JSON.parse(localStorage.getItem('sb_alerts') || '[]') } catch(e) { return [] } })
  const [showLockModal, setShowLockModal] = useState(false)
  const [showUnlockModal, setShowUnlockModal] = useState(false)
  const [lockPinEntry, setLockPinEntry] = useState('')
  const [lockPinError, setLockPinError] = useState(false)
  const [awaySummary, setAwaySummary] = useState(null)
  const [lockPin, setLockPin] = useState(() => localStorage.getItem('sb_pin') || '4729')
  const [lockWebhook, setLockWebhook] = useState(() => localStorage.getItem('sb_lock_webhook') || '')
  const [lockNote, setLockNote] = useState(() => localStorage.getItem('sb_lock_note') || 'Hemi Walker')

  // Pending tools from AI match (before adding to basket)
  const [pendingTools, setPendingTools] = useState([]) // string[]


  // Job search combobox state
  const [jobSearch, setJobSearch] = useState('')
  const [jobDropOpen, setJobDropOpen] = useState(false)
  const [basketJobSearch, setBasketJobSearch] = useState('')
  const [basketJobDropOpen, setBasketJobDropOpen] = useState(false)
  const [editJobSearch, setEditJobSearch] = useState('')
  const [editJobDropOpen, setEditJobDropOpen] = useState(false)
  const [editToolJobSearch, setEditToolJobSearch] = useState('')
  const [editToolJobDropOpen, setEditToolJobDropOpen] = useState(false)
  const jobSearchRef = useRef(null)
  const basketJobSearchRef = useRef(null)
  const editJobSearchRef = useRef(null)
  const editToolJobSearchRef = useRef(null)

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

  // ── Day Works ────────────────────────────────────────────────────
  const [dwView, setDwView] = useState('new') // 'new' | 'log'
  const [dwStep, setDwStep] = useState('form') // 'form' | 'complete' | 'pdfPreview'
  const [dwJob, setDwJob] = useState('')
  const [dwDate, setDwDate] = useState(() => dwTodayISO())
  const [dwVariation, setDwVariation] = useState('')
  const [dwVoNumber, setDwVoNumber] = useState('')
  const [dwLocation, setDwLocation] = useState('')
  const [dwLabourRows, setDwLabourRows] = useState([])
  const [dwMaterialRows, setDwMaterialRows] = useState([])
  const [dwComments, setDwComments] = useState('')
  const [dwPhotos, setDwPhotos] = useState([])
  const [dwCaptureText, setDwCaptureText] = useState('')
  const [dwLastParsed, setDwLastParsed] = useState(null)
  const [dwSignoffMode, setDwSignoffMode] = useState('glass')
  const [dwClientName, setDwClientName] = useState('')
  const [dwClientEmail, setDwClientEmail] = useState('')
  const [dwSigned, setDwSigned] = useState(false)
  const [dwValidationMsg, setDwValidationMsg] = useState('')
  const [dwActiveTab, setDwActiveTab] = useState('details')
  const [dwInputMode, setDwInputMode] = useState('voice')
  const [dwListening, setDwListening] = useState(false)
  const [dwSubmitting, setDwSubmitting] = useState(false)
  const [dwLastSubmitted, setDwLastSubmitted] = useState(null)

  const [dwEntries, setDwEntries] = useState([])
  const [dwFilterJob, setDwFilterJob] = useState('')
  const [dwFilterVariation, setDwFilterVariation] = useState('all')
  const [dwFilterStatus, setDwFilterStatus] = useState('all')

  const [dwJobSearch, setDwJobSearch] = useState('')
  const [dwJobDropOpen, setDwJobDropOpen] = useState(false)
  const dwJobSearchRef = useRef(null)

  const [dwWebhookUrl, setDwWebhookUrl] = useState(() => localStorage.getItem('sb_dayworks_webhook') || '')

  const dwRecognitionRef = useRef(null)
  const dwFileInputRef = useRef(null)
  const dwSigCanvasRef = useRef(null)
  const dwDrawingRef = useRef(false)
  const dwIdSeqRef = useRef(1)

  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')
  const lastChunkRef = useRef('')

  // Close job dropdowns on outside click
  useEffect(() => {
    function handleClick(e) {
      if (jobSearchRef.current && !jobSearchRef.current.contains(e.target)) setJobDropOpen(false)
      if (editJobSearchRef.current && !editJobSearchRef.current.contains(e.target)) setEditJobDropOpen(false)
      if (editToolJobSearchRef.current && !editToolJobSearchRef.current.contains(e.target)) setEditToolJobDropOpen(false)
      if (basketJobSearchRef.current && !basketJobSearchRef.current.contains(e.target)) setBasketJobDropOpen(false)
      if (dwJobSearchRef.current && !dwJobSearchRef.current.contains(e.target)) setDwJobDropOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Sync jobSearch display text when AI fills in form.job
  useEffect(() => {
    if (form.job) setJobSearch(form.job)
    else setJobSearch('')
  }, [form.job])

  useEffect(() => {
    loadEntries()
    loadToolEntries()
    loadDayworksEntries()
    fetch('/api/jobs').then(r => r.json()).then(setJobs).catch(() => {})
    fetch('/api/hand-tools').then(r => r.json()).then(setHandTools).catch(() => {})
    fetch('/api/products').then(r => r.json()).then(setProducts).catch(() => {})
    fetch('/api/vos').then(r => r.json()).then(setVos).catch(() => {})
  }, [])

  async function loadDayworksEntries() {
    try {
      const r = await fetch('/api/dayworks')
      setDwEntries(await r.json())
    } catch {}
  }

  useEffect(() => {
    if (tab === 'settings') loadWebhookStatus()
  }, [tab])

  async function loadEntries() {
    try {
      const r = await fetch('/api/entries')
      setEntries(await r.json())
    } catch {}
  }

  async function loadToolEntries() {
    try {
      const r = await fetch('/api/tool-entries')
      setToolEntries(await r.json())
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
    alert(
      'Speech recognition not supported.\nPlease use Safari on iPhone, or Chrome on Android/desktop.'
    )
    return
  }

  const rec = new SR()

  rec.continuous = true
  rec.interimResults = true
  rec.lang = 'en-NZ'
  rec.maxAlternatives = 1

  recognitionRef.current = rec
  transcriptRef.current = ''
  lastChunkRef.current = ''
  setTranscript('')

  rec.onstart = () => setListening(true)

  rec.onresult = (e) => {
    let updatedTranscript = transcriptRef.current

    for (let i = e.resultIndex; i < e.results.length; i++) {
      const result = e.results[i]
      const chunk = result[0].transcript.trim()

      // Samsung / Android duplicate protection
      if (
        result.isFinal &&
        chunk &&
        chunk !== lastChunkRef.current
      ) {
        updatedTranscript +=
          (updatedTranscript ? ' ' : '') + chunk

        lastChunkRef.current = chunk
      }
    }

    transcriptRef.current = updatedTranscript
    setTranscript(updatedTranscript)

    // Temporary debugging — remove later if desired
    console.log('Speech event:', {
      resultIndex: e.resultIndex,
      transcript: updatedTranscript,
      results: e.results.length,
    })
  }

  rec.onend = () => {
    setListening(false)
  }

  rec.onerror = (err) => {
    console.error('Speech recognition error:', err)
    setListening(false)
  }

  rec.start()
}
  async function handleTranscript(text) {
    setProcessing(true)
    setMatchResult(null)
    setConfirmedProducts([])
    setPendingTools([])
    try {
      const r = await fetch('/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: text }),
      })
      if (!r.ok) throw new Error(`Server error ${r.status}: ${(await r.text()).slice(0, 200)}`)
      const data = await r.json()
      setMatchResult(data)
      // Populate pending tools from AI response — normalise to [{name, quantity}]
      if (data.tools?.length > 0) setPendingTools(data.tools.map(t =>
        typeof t === 'string' ? { name: t, quantity: 1 } : { name: t.name, quantity: t.quantity ?? 1 }
      ))
      // Seed confirmedProducts from all non-ambiguous matches
      if (data.matches?.length > 0 && !data.ambiguous) {
        setConfirmedProducts(data.matches.map(m => ({
          ...m,
          quantity: m.quantity != null ? String(m.quantity) : '',
        })))
      }
      setForm({
        job: data.job || '',
        worker_name: data.worker_name || '',
      })
    } catch (e) {
      showToast('Error: ' + (e?.message || 'contacting server'))
    }
    setProcessing(false)
  }

  async function submitEntry() {
    if (!canSubmit) return
    try {
      // Save all stock entries
      for (const p of confirmedProducts) {
        await fetch('/api/entries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            item_code: p.code,
            job: form.job,
            supplier: p.supplier,
            description: p.description,
            cost_quantity: parseFloat(p.quantity),
            unit: p.unit,
            gl_code: p.gl || '',
            worker_name: form.worker_name,
            source: inputMode,
          }),
        })
      }

      // Save any pending tools
      const savedTools = []
      for (const tool of pendingTools) {
        const qty = parseInt(tool.quantity) || 1
        await fetch('/api/tool-entries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_name: tool.name, job: form.job, worker_name: form.worker_name, quantity: qty, source: inputMode }),
        })
        savedTools.push({ ...tool, quantity: qty })
      }

      // Update basket
      const newBasketItems = [
        ...confirmedProducts.map(p => ({ type: 'stock', product: p, quantity: parseFloat(p.quantity) })),
        ...savedTools.map(t => ({ type: 'tool', toolName: t.name, quantity: t.quantity })),
      ]
      setBasket(b => [...b, ...newBasketItems])
      if (!basketJob && form.job) { setBasketJob(form.job); setBasketJobSearch(form.job) }
      if (!basketWorker && form.worker_name) setBasketWorker(form.worker_name)

      // ── Room lock alert ──────────────────────────────────────────────
      if (roomLocked) {
        const alertItems = confirmedProducts.map(p => ({ code: p.code, desc: p.description, qty: parseFloat(p.quantity), unit: p.unit, worker: form.worker_name, job: form.job, time: new Date().toISOString() }))
        setLockAlerts(prev => [...prev, ...alertItems])
        sendLockAlert(alertItems)
      }

      const productMsg = confirmedProducts.length > 0 ? `${confirmedProducts.length} product${confirmedProducts.length > 1 ? 's' : ''}` : ''
      const toolMsg = savedTools.length > 0 ? `${productMsg ? ' + ' : ''}${savedTools.length} tool${savedTools.length > 1 ? 's' : ''}` : ''
      showToast(`${productMsg}${toolMsg} added to basket ✓`)
      loadEntries()
      loadToolEntries()
      setTranscript(''); setTextInput(''); setMatchResult(null)
      setConfirmedProducts([]); setPendingTools([])
      setJobDropOpen(false)
    } catch { showToast('Save failed — try again') }
  }

  async function submitBasketAll() {
    if (basket.length === 0) return
    showToast(`${basket.length} entr${basket.length === 1 ? 'y' : 'ies'} already saved ✓`)
    setBasket([])
    setBasketJob(''); setBasketJobSearch('')
    setBasketWorker('')
    resetCapture()
  }


  function resetCapture() {
    setTranscript(''); setTextInput(''); setMatchResult(null)
    setConfirmedProducts([]); setForm({ job: '', worker_name: '' })
    setJobSearch(''); setJobDropOpen(false); setPendingTools([])
    setBasket([]); setBasketJob(''); setBasketJobSearch(''); setBasketWorker('')
  }

  async function deleteEntry(id) {
    await fetch(`/api/entries/${id}`, { method: 'DELETE' })
    loadEntries()
  }

  async function deleteToolEntry(id) {
    await fetch(`/api/tool-entries/${id}`, { method: 'DELETE' })
    loadToolEntries()
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

  async function saveEditToolEntry() {
    try {
      await fetch(`/api/tool-entries/${editingToolEntry.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job: editToolForm.job,
          quantity: parseFloat(editToolForm.quantity),
          worker_name: editToolForm.worker_name,
        }),
      })
      showToast('Tool entry updated ✓')
      setEditingToolEntry(null)
      loadToolEntries()
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

  function buildToolExportUrl() {
    const params = new URLSearchParams()
    if (exportFrom) params.set('date_from', toISODate(exportFrom))
    if (exportTo) params.set('date_to', toISODate(exportTo))
    const qs = params.toString()
    return `/api/tool-entries/export${qs ? '?' + qs : ''}`
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

  // ── Lock persistence ──────────────────────────────────────────────
  useEffect(() => {
    localStorage.setItem('sb_locked', roomLocked)
    if (awaySince) localStorage.setItem('sb_since', String(awaySince))
    else localStorage.removeItem('sb_since')
    localStorage.setItem('sb_alerts', JSON.stringify(lockAlerts))
  }, [roomLocked, awaySince, lockAlerts])

  // ── Pack-size helpers ─────────────────────────────────────────────
  function packInfo(product) {
    if (!product) return null
    const text = (product.description || '').toLowerCase()
    let m = text.match(/box of ([\d,]+)/)
    if (m) return { pack: parseInt(m[1].replace(/,/g, '')), label: 'box of ' + m[1] }
    m = text.match(/([\d,]+)\s*per\s*(?:box|bag|carton|ctn)/)
    if (m) return { pack: parseInt(m[1].replace(/,/g, '')), label: m[1] + ' per pack' }
    return null
  }
  const COUNT_UNITS_LK = ['ROLL','BAG','BOX','PAIL','KIT','EA','SHEET','CTN','CAN','M2']
  function qtyWarn(product, qty) {
    const n = parseFloat(qty)
    if (!(n > 0)) return null
    const pk = packInfo(product)
    if (pk && n >= pk.pack && n % pk.pack === 0) return { suggest: n / pk.pack, msg: n + ' sounds like the piece count — that\'s ' + (n / pk.pack) + ' ' + product.unit + ' (each = ' + pk.label + ')' }
    if (pk && n > pk.pack) { const sg = Math.round(n / pk.pack); return { suggest: sg, msg: 'Counted in ' + product.unit + ' (each = ' + pk.label + '). Did you mean ' + sg + '?' } }
    if (COUNT_UNITS_LK.includes((product.unit || '').toUpperCase()) && n > 50) return { suggest: null, msg: 'That\'s a lot of ' + product.unit + ' — double-check.' }
    return null
  }
  function fmtLockDur(ms) {
    const m = Math.round(ms / 60000)
    if (m < 1) return 'under a minute'
    if (m < 60) return m + ' min'
    const h = Math.floor(m / 60); return h + 'h ' + (m % 60) + 'm'
  }
  async function sendLockAlert(entries) {
    if (!lockWebhook) return
    try {
      await fetch(lockWebhook, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'stock_taken_while_locked', locked_by: lockNote, entries, at: new Date().toISOString() }) })
    } catch(e) {}
  }
  function doLock() {
    setRoomLocked(true); setAwaySince(Date.now()); setLockAlerts([]); setShowLockModal(false)
    showToast('Room locked — you\'ll be alerted to anything taken')
  }
  function doUnlock(pin) {
    if (pin !== lockPin) { setLockPinError(true); setLockPinEntry(''); return }
    const dur = fmtLockDur(Date.now() - (awaySince || Date.now()))
    setAwaySummary({ dur, items: lockAlerts.slice() })
    setRoomLocked(false); setAwaySince(null); setLockAlerts([])
    setShowUnlockModal(false); setLockPinEntry(''); setLockPinError(false)
  }
  function handleLockPin(d) {
    if (lockPinEntry.length >= 4) return
    const v = lockPinEntry + d
    setLockPinEntry(v); setLockPinError(false)
    if (v.length === 4) setTimeout(() => doUnlock(v), 130)
  }

  // ── Day Works handlers ──────────────────────────────────────────────
  function dwSetTab(id) { setDwActiveTab(id); setDwValidationMsg('') }

  function dwGoPrevTab() {
    const idx = DW_TABS.findIndex(t => t.id === dwActiveTab)
    if (idx > 0) { setDwActiveTab(DW_TABS[idx - 1].id); setDwValidationMsg('') }
  }

  function dwGoNext() {
    const idx = DW_TABS.findIndex(t => t.id === dwActiveTab)
    if (dwActiveTab === 'details') {
      if (!dwJob) { setDwValidationMsg('Job Name is required.'); return }
      if (!dwVariation) { setDwValidationMsg('Select whether this is Variation Work.'); return }
      if (dwVariation === 'Yes' && !dwVoNumber) { setDwValidationMsg('Select a Variation Number.'); return }
    }
    if (idx < DW_TABS.length - 1) { setDwActiveTab(DW_TABS[idx + 1].id); setDwValidationMsg('') }
  }

  function dwOnCaptureSubmit(overrideText) {
    const text = (overrideText ?? dwCaptureText).trim()
    if (!text) return
    const lower = text.toLowerCase()
    const looksLikeLabour = /(am|pm|start|finish|worked|working)/i.test(lower)
    const looksLikeMaterial = /^\s*\d/.test(text) || DW_UNIT_WORDS.some(u => new RegExp(`\\d+\\s*${u}\\b`, 'i').test(lower))

    if (looksLikeLabour) {
      const nameMatch = text.match(/^([A-Za-z]+(?:\s[A-Za-z]+)?)\s+(?:was|worked|is)/i)
      const name = nameMatch ? nameMatch[1] : text.split(' ')[0]
      const times = [...lower.matchAll(/\d{1,2}(?::\d{2})?\s*(?:am|pm)/gi)].map(m => m[0])
      const startRaw = times[0], endRaw = times[1]
      const startMin = startRaw ? dwParseTimeToMinutes(startRaw) : null
      const endMin = endRaw ? dwParseTimeToMinutes(endRaw) : null
      let hoursLabel = '—'
      if (startMin != null && endMin != null) {
        let diff = endMin - startMin
        if (diff < 0) diff += 24 * 60
        hoursLabel = (diff / 60).toFixed(1).replace(/\.0$/, '') + ' hrs'
      }
      const activityMatch = text.match(/on ([a-zA-Z\s]+?)(?:\.|$)/i)
      const activity = activityMatch ? activityMatch[1].trim() : 'General labour'
      const row = {
        id: dwIdSeqRef.current++, name, activity,
        start: startRaw ? dwFormatMinutes(startMin) : '—',
        end: endRaw ? dwFormatMinutes(endMin) : '—',
        hoursLabel,
      }
      setDwLabourRows(rows => [...rows, row])
      setDwCaptureText('')
      setDwActiveTab('labour')
      setDwLastParsed({ type: 'labour', id: row.id, summary: `Added ${name} · ${row.hoursLabel} (${activity})` })
      return
    }

    if (looksLikeMaterial) {
      const qtyMatch = text.match(/(\d+(?:\.\d+)?)/)
      const qty = qtyMatch ? qtyMatch[1] : ''
      const unitMatch = lower.match(new RegExp(`\\b(${DW_UNIT_WORDS.join('|')})\\b`))
      const unit = unitMatch ? unitMatch[1] : ''
      let item = text
      const ofMatch = text.match(/of\s+(.+)$/i)
      if (ofMatch) item = ofMatch[1]
      else if (unitMatch) item = text.slice(text.toLowerCase().indexOf(unitMatch[1]) + unitMatch[1].length).replace(/^of\s+/i, '').trim()
      item = item.trim().replace(/\.$/, '') || text
      const row = { id: dwIdSeqRef.current++, item, unit: unit || 'unit', qty: qty || '1' }
      setDwMaterialRows(rows => [...rows, row])
      setDwCaptureText('')
      setDwActiveTab('materials')
      setDwLastParsed({ type: 'material', id: row.id, summary: `Added ${qty || 1} ${unit || 'unit'} — ${item}` })
      return
    }

    setDwLastParsed({ type: 'unknown', id: null, summary: `Couldn't tell if that's labour or materials — try "Steve worked 9am-5pm" or "20 bags of cement"` })
    setDwCaptureText('')
  }

  function dwOnCaptureKeyDown(e) { if (e.key === 'Enter') dwOnCaptureSubmit() }

  function dwUndoLast() {
    if (!dwLastParsed) return
    if (dwLastParsed.type === 'labour') setDwLabourRows(rows => rows.filter(r => r.id !== dwLastParsed.id))
    else if (dwLastParsed.type === 'material') setDwMaterialRows(rows => rows.filter(r => r.id !== dwLastParsed.id))
    setDwLastParsed(null)
  }

  function dwDeleteLabourRow(id) { setDwLabourRows(rows => rows.filter(r => r.id !== id)) }
  function dwDeleteMaterialRow(id) { setDwMaterialRows(rows => rows.filter(r => r.id !== id)) }

  function dwToggleListen() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      setDwLastParsed({ type: 'unsupported', id: null, summary: "Voice input isn't supported in this browser (common on Safari/iPhone) — switch to Text instead." })
      return
    }
    if (dwListening) { dwRecognitionRef.current?.stop(); return }
    const rec = new SR()
    rec.lang = 'en-NZ'
    rec.onresult = (ev) => {
      const text = ev.results[0][0].transcript
      setDwCaptureText(text)
      dwOnCaptureSubmit(text)
    }
    rec.onend = () => setDwListening(false)
    rec.onerror = () => setDwListening(false)
    dwRecognitionRef.current = rec
    setDwListening(true)
    rec.start()
  }

  function dwOpenCamera() { dwFileInputRef.current && dwFileInputRef.current.click() }
  function dwOnFilesSelected(e) {
    const files = Array.from(e.target.files || [])
    files.forEach((f) => {
      const reader = new FileReader()
      reader.onload = () => setDwPhotos(p => [...p, { id: dwIdSeqRef.current++, src: reader.result }])
      reader.readAsDataURL(f)
    })
    e.target.value = ''
  }
  function dwRemovePhoto(id) { setDwPhotos(p => p.filter(x => x.id !== id)) }

  function dwGetPos(e) {
    const canvas = dwSigCanvasRef.current
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY }
  }
  function dwOnSigDown(e) {
    dwDrawingRef.current = true
    const ctx = dwSigCanvasRef.current.getContext('2d')
    const p = dwGetPos(e)
    ctx.strokeStyle = '#e8ecf2'; ctx.lineWidth = 2.2; ctx.lineCap = 'round'
    ctx.beginPath(); ctx.moveTo(p.x, p.y)
    setDwSigned(true)
  }
  function dwOnSigMove(e) {
    if (!dwDrawingRef.current) return
    const ctx = dwSigCanvasRef.current.getContext('2d')
    const p = dwGetPos(e)
    ctx.lineTo(p.x, p.y); ctx.stroke()
  }
  function dwOnSigUp() { dwDrawingRef.current = false }
  function dwClearSignature() {
    const canvas = dwSigCanvasRef.current
    if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height)
    setDwSigned(false)
  }

  function dwResetForm() {
    setDwJob(''); setDwJobSearch(''); setDwJobDropOpen(false)
    setDwDate(dwTodayISO()); setDwVariation(''); setDwVoNumber(''); setDwLocation('')
    setDwLabourRows([]); setDwMaterialRows([]); setDwComments(''); setDwPhotos([])
    setDwCaptureText(''); setDwLastParsed(null); setDwSignoffMode('glass'); setDwClientName(''); setDwClientEmail('')
    setDwSigned(false); setDwValidationMsg(''); setDwActiveTab('details'); setDwInputMode('voice')
    dwClearSignature()
    setDwStep('form')
  }

  function dwStartNew() { dwResetForm(); setDwView('new') }

  async function dwSendWebhook(entry) {
    if (!dwWebhookUrl) return
    try {
      await fetch(dwWebhookUrl, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'dayworks_sheet_submitted', entry, at: new Date().toISOString() }),
      })
    } catch (e) {}
  }

  async function dwSubmitForm() {
    if (!dwJob || !dwVariation) {
      setDwActiveTab('details'); setDwValidationMsg('Job Name and Variation Work are required.'); return
    }
    if (dwVariation === 'Yes' && !dwVoNumber) {
      setDwActiveTab('details'); setDwValidationMsg('Select a Variation Number.'); return
    }
    if (dwSignoffMode === 'glass' && !dwSigned) {
      setDwActiveTab('signoff'); setDwValidationMsg('The client needs to sign before submitting.'); return
    }
    if (dwSignoffMode === 'email' && !dwClientEmail) {
      setDwActiveTab('signoff'); setDwValidationMsg("Enter the client's email."); return
    }
    setDwSubmitting(true)
    const signatureDataUrl = dwSignoffMode === 'glass' && dwSigCanvasRef.current ? dwSigCanvasRef.current.toDataURL() : null
    const payload = {
      job: dwJob, date: dwDate, variation: dwVariation, vo_number: dwVariation === 'Yes' ? dwVoNumber : null,
      location: dwLocation, labour_rows: dwLabourRows, material_rows: dwMaterialRows, comments: dwComments,
      photos: dwPhotos, signoff_mode: dwSignoffMode, client_name: dwClientName || null,
      client_email: dwSignoffMode === 'email' ? dwClientEmail : null,
      signature_data_url: signatureDataUrl,
      status: dwSignoffMode === 'glass' ? 'Signed on glass' : 'Sent to client',
    }
    try {
      const r = await fetch('/api/dayworks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error('save failed')
      const saved = await r.json()
      dwSendWebhook(saved)
      setDwLastSubmitted(saved)
      setDwStep('complete')
      setDwValidationMsg('')
      loadDayworksEntries()
    } catch (e) {
      showToast('Save failed — try again')
    }
    setDwSubmitting(false)
  }

  const hasMatches = matchResult?.matches?.length > 0
  const isAmbiguous = matchResult?.ambiguous && matchResult?.matches?.length > 1
  const canSubmit = confirmedProducts.length > 0
    && confirmedProducts.every(p => p.quantity && String(p.quantity).trim() !== '')
    && confirmedProducts.every(p => !qtyWarn(p, p.quantity) || p._qtyAck)
    && form.job.trim()
    && form.worker_name.trim()


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
          {[['capture','⬤ Capture'],['log','☰ Log'],['dayworks','🧾 Day Works'],['reference','📋 Reference'],['qr','⊞ QR'],['settings','⚙ Settings']].map(([t,label]) => (
            <button key={t} style={S.tab(tab===t)} onClick={() => setTab(t)}>{label}</button>
          ))}
        </div>
        {/* Room lock status pill */}
        {roomLocked ? (
          <button onClick={() => setShowUnlockModal(true)} style={{ display:'flex', alignItems:'center', gap:9, background:'rgba(232,163,61,.12)', border:'1.5px solid #E8A33D', borderRadius:8, padding:'6px 14px', cursor:'pointer' }}>
            <span style={{fontSize:17}}>🔒</span>
            <span style={{display:'flex', flexDirection:'column', alignItems:'flex-start', lineHeight:1.1}}>
              <span style={{fontFamily:'var(--font-head)', fontWeight:800, fontSize:13, letterSpacing:1, color:'#E8A33D'}}>ROOM LOCKED</span>
              <span style={{fontSize:10, color:'#c79a55'}}>{lockNote} away · tap to unlock</span>
            </span>
          </button>
        ) : (
          <button onClick={() => setShowLockModal(true)} style={{ display:'flex', alignItems:'center', gap:9, background:'rgba(76,175,125,.08)', border:'1.5px solid rgba(76,175,125,.5)', borderRadius:8, padding:'6px 14px', cursor:'pointer' }}>
            <span style={{width:9, height:9, borderRadius:'50%', background:'var(--success)', boxShadow:'0 0 6px var(--success)'}}></span>
            <span style={{fontFamily:'var(--font-head)', fontWeight:700, fontSize:13, letterSpacing:1, color:'var(--success)'}}>ROOM OPEN</span>
          </button>
        )}

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

      {/* Away locked banner */}
      {roomLocked && (
        <div style={{background:'rgba(232,163,61,.13)', borderBottom:'1px solid rgba(232,163,61,.4)', padding:'10px 22px', display:'flex', alignItems:'center', justifyContent:'center', gap:10, textAlign:'center'}}>
          <span style={{width:8, height:8, borderRadius:'50%', background:'#E8A33D', flexShrink:0}}></span>
          <span style={{fontSize:13, color:'#e3c389', lineHeight:1.4}}><strong style={{fontFamily:'var(--font-head)', color:'#E8A33D'}}>ROOM LOCKED</strong> — {lockNote} is away. Stock taken now is logged and you'll be alerted automatically.</span>
        </div>
      )}

      {/* ── MOBILE BOTTOM NAV ────────────────────────────────────────── */}
      <nav className="mobile-bottom-nav" style={{
        display: 'none', position: 'fixed', bottom: 0, left: 0, right: 0,
        background: 'var(--surface)', borderTop: '2px solid var(--accent)',
        zIndex: 200, padding: '8px 0 max(8px, env(safe-area-inset-bottom))',
      }}>
        {[
          ['capture', '⬤', 'Capture'],
          ['log', '☰', 'Log'],
          ['dayworks', '🧾', 'Dayworks'],
          ['reference', '📋', 'Reference'],
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

      {/* ── LOCK MODAL ── */}
      {showLockModal && (
        <div onClick={() => setShowLockModal(false)} style={{position:'fixed',inset:0,background:'rgba(0,0,0,.72)',zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',padding:20}}>
          <div onClick={e => e.stopPropagation()} style={{background:'var(--surface)',border:'1px solid var(--border)',borderRadius:16,padding:28,width:'100%',maxWidth:460}}>
            <div style={{fontFamily:'var(--font-head)',fontSize:20,fontWeight:800,letterSpacing:1,textTransform:'uppercase',color:'var(--text)',marginBottom:8}}>🔒 Lock the room?</div>
            <div style={{fontSize:14,color:'var(--muted)',lineHeight:1.6,marginBottom:20}}>You're heading out. While locked, the app stays usable — but <strong style={{color:'var(--text)'}}>anyone who takes stock must log it</strong>, and you'll get an instant alert.</div>
            <div style={{marginBottom:20}}>
              <div style={{fontFamily:'var(--font-head)',fontSize:11,fontWeight:700,letterSpacing:1.5,textTransform:'uppercase',color:'var(--muted)',marginBottom:8}}>Alert recipient name (for the notification)</div>
              <input value={lockNote} onChange={e => { setLockNote(e.target.value); localStorage.setItem('sb_lock_note', e.target.value) }} style={{...S.fieldInput}} placeholder="e.g. Hemi Walker" />
              <div style={{fontFamily:'var(--font-head)',fontSize:11,fontWeight:700,letterSpacing:1.5,textTransform:'uppercase',color:'var(--muted)',marginBottom:8,marginTop:12}}>Webhook URL (Make / Zapier — optional)</div>
              <input value={lockWebhook} onChange={e => { setLockWebhook(e.target.value); localStorage.setItem('sb_lock_webhook', e.target.value) }} style={{...S.fieldInput}} placeholder="https://hook.make.com/..." />
              <div style={{fontFamily:'var(--font-head)',fontSize:11,fontWeight:700,letterSpacing:1.5,textTransform:'uppercase',color:'var(--muted)',marginBottom:8,marginTop:12}}>Unlock PIN</div>
              <input value={lockPin} onChange={e => { setLockPin(e.target.value); localStorage.setItem('sb_pin', e.target.value) }} style={{...S.fieldInput,maxWidth:140}} placeholder="4729" maxLength={6} />
            </div>
            <div style={{display:'flex',gap:10}}>
              <button style={S.btnSecondary} onClick={() => setShowLockModal(false)}>Cancel</button>
              <button style={{...S.btnPrimary(true),flex:1,background:'#E8A33D',color:'#1a1206'}} onClick={doLock}>🔒 Lock &amp; Go</button>
            </div>
          </div>
        </div>
      )}

      {/* ── UNLOCK PIN MODAL ── */}
      {showUnlockModal && (
        <div onClick={() => setShowUnlockModal(false)} style={{position:'fixed',inset:0,background:'rgba(0,0,0,.78)',zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',padding:20}}>
          <div onClick={e => e.stopPropagation()} style={{background:'var(--surface)',border:'1px solid var(--border)',borderRadius:16,padding:28,width:'100%',maxWidth:360,textAlign:'center'}}>
            <div style={{fontFamily:'var(--font-head)',fontSize:20,fontWeight:800,letterSpacing:1,textTransform:'uppercase',color:'var(--text)',marginBottom:6}}>Unlock Room</div>
            <div style={{fontSize:13,color:'var(--muted)',marginBottom:18}}>Enter your 4-digit PIN</div>
            <div style={{display:'flex',justifyContent:'center',gap:12,marginBottom:8}}>
              {[0,1,2,3].map(idx => <div key={idx} style={{width:14,height:14,borderRadius:'50%',background:idx<lockPinEntry.length?'var(--accent)':'transparent',border:'2px solid '+(idx<lockPinEntry.length?'var(--accent)':'var(--border)')}}></div>)}
            </div>
            {lockPinError && <div style={{color:'var(--danger)',fontSize:13,marginBottom:8,fontFamily:'var(--font-head)'}}>Wrong PIN — try again</div>}
            <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:10,maxWidth:260,margin:'16px auto 0'}}>
              {['1','2','3','4','5','6','7','8','9'].map(d => <button key={d} onClick={() => handleLockPin(d)} style={{height:64,borderRadius:12,background:'var(--surface2)',border:'1px solid var(--border)',color:'var(--text)',fontFamily:'var(--font-head)',fontWeight:700,fontSize:26,cursor:'pointer'}}>{d}</button>)}
              <button onClick={() => { setLockPinEntry(''); setLockPinError(false) }} style={{height:64,borderRadius:12,background:'transparent',border:'1px solid var(--border)',color:'var(--muted)',fontFamily:'var(--font-head)',fontWeight:700,fontSize:16,cursor:'pointer'}}>C</button>
              <button onClick={() => handleLockPin('0')} style={{height:64,borderRadius:12,background:'var(--surface2)',border:'1px solid var(--border)',color:'var(--text)',fontFamily:'var(--font-head)',fontWeight:700,fontSize:26,cursor:'pointer'}}>0</button>
              <button onClick={() => setLockPinEntry(p => p.slice(0,-1))} style={{height:64,borderRadius:12,background:'transparent',border:'1px solid var(--border)',color:'var(--muted)',fontSize:22,cursor:'pointer'}}>⌫</button>
            </div>
          </div>
        </div>
      )}

      {/* ── AWAY SUMMARY MODAL ── */}
      {awaySummary && (
        <div onClick={() => setAwaySummary(null)} style={{position:'fixed',inset:0,background:'rgba(0,0,0,.78)',zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',padding:20}}>
          <div onClick={e => e.stopPropagation()} style={{background:'var(--surface)',border:'1px solid var(--border)',borderRadius:16,padding:28,width:'100%',maxWidth:500,maxHeight:'85vh',overflowY:'auto'}}>
            <div style={{fontFamily:'var(--font-head)',fontSize:20,fontWeight:800,letterSpacing:1,textTransform:'uppercase',color:'var(--text)',marginBottom:6}}>🔓 Welcome back</div>
            <div style={{fontSize:14,color:'var(--muted)',marginBottom:18}}>Room was locked for <strong style={{color:'var(--text)'}}>{awaySummary.dur}</strong>.</div>
            {awaySummary.items.length === 0 ? (
              <div style={{textAlign:'center',padding:'20px 0 28px'}}>
                <div style={{fontSize:36,marginBottom:10}}>✅</div>
                <div style={{fontFamily:'var(--font-head)',fontSize:18,color:'var(--success)'}}>All quiet — nothing was taken</div>
              </div>
            ) : (
              <>
                <div style={{display:'flex',gap:12,marginBottom:18}}>
                  <div style={{flex:1,background:'var(--surface2)',borderRadius:10,padding:'12px 16px'}}><div style={{fontFamily:'var(--font-head)',fontSize:28,fontWeight:800,color:'#E8A33D'}}>{awaySummary.items.length}</div><div style={{fontSize:11,color:'var(--muted)',fontFamily:'var(--font-head)',letterSpacing:1}}>ITEMS TAKEN</div></div>
                  <div style={{flex:1,background:'var(--surface2)',borderRadius:10,padding:'12px 16px'}}><div style={{fontFamily:'var(--font-head)',fontSize:28,fontWeight:800,color:'var(--accent)'}}>{[...new Set(awaySummary.items.map(a => a.worker))].length}</div><div style={{fontSize:11,color:'var(--muted)',fontFamily:'var(--font-head)',letterSpacing:1}}>PEOPLE</div></div>
                </div>
                {awaySummary.items.map((a, idx) => (
                  <div key={idx} style={{padding:'12px 14px',background:'var(--surface2)',border:'1px solid rgba(232,163,61,.3)',borderRadius:10,marginBottom:8}}>
                    <div style={{display:'flex',justifyContent:'space-between',gap:8}}><span style={{fontFamily:'var(--font-head)',fontWeight:700,color:'var(--accent)'}}>{a.code}</span><span style={{fontFamily:'var(--font-head)',fontWeight:700,color:'var(--text)'}}>×{a.qty} {a.unit}</span></div>
                    <div style={{fontSize:12,color:'var(--muted)',marginTop:3}}>{a.worker} · {a.job}</div>
                  </div>
                ))}
              </>
            )}
            <button style={{...S.btnPrimary(true),width:'100%',marginTop:12}} onClick={() => setAwaySummary(null)}>Got it</button>
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
                    Say it all in one go — multiple products, tools, the job and your name. Tap the mic and the app splits it into lines you can check.<br/>
                    <em style={{color:'var(--accent)'}}>e.g. "Bag of waterstop and two Bituthene 5000 rolls to building G, plus a handsaw and hammer — it's Tony"</em>
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
                    Say it all in one go — multiple products, tools, the job and your name. The app splits it into lines you can check.<br/>
                    <em style={{color:'var(--accent)'}}>e.g. "Bag of waterstop and two Bituthene 5000 rolls to building G, plus a handsaw and hammer — it's Tony"</em>
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
              <div style={S.processing}><div style={S.spinner} />Matching products &amp; tools…</div>
            )}

            {!processing && isAmbiguous && (
              <div style={S.card}>
                <div style={{...S.titleAccent, color:'var(--text)', fontSize:15}}>
                  Multiple products found — which one?
                </div>
                {matchResult.matches.map(p => (
                  <div key={p.code} style={S.productOption(confirmedProducts.some(c => c.code === p.code))}
                    onClick={() => setConfirmedProducts([{ ...p, quantity: p.quantity != null ? String(p.quantity) : '' }])}>
                    <div style={S.productCode}>{p.code}</div>
                    <div>
                      <div style={S.productDesc}>{p.description}</div>
                      <div style={S.productSupplier}>{p.supplier} · <span style={{color:'var(--accent)'}}>{p.unit}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!processing && hasMatches && confirmedProducts.length > 0 && (
              <div style={S.cardAccent}>
                <div style={S.titleAccent}>
                  Confirm {confirmedProducts.length > 1 ? `${confirmedProducts.length} Products` : 'Entry'}
                </div>

                {/* One row per product, each with its own qty input */}
                {confirmedProducts.map((p, i) => {
                  const missingQty = !p.quantity || String(p.quantity).trim() === ''
                  const warn = !missingQty ? qtyWarn(p, p.quantity) : null
                  const showWarn = warn && !p._qtyAck
                  return (
                    <div key={p.code} style={{
                      background: 'var(--surface2)', borderRadius: 8, padding: '12px 16px',
                      marginBottom: 10,
                      border: `1px solid ${missingQty ? 'var(--danger)' : showWarn ? '#E8A33D' : 'var(--border)'}`,
                    }}>
                      <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:12}}>
                        <div style={{flex:1, minWidth:0}}>
                          <div style={{fontFamily:'var(--font-head)', fontSize:16, fontWeight:700, color:'var(--accent)'}}>{p.code}</div>
                          <div style={{fontSize:13, color:'var(--text)', marginTop:2}}>{p.description}</div>
                          <div style={{fontSize:11, color:'var(--muted)', marginTop:2}}>{p.supplier}</div>
                        </div>
                        <div style={{display:'flex', flexDirection:'column', alignItems:'flex-end', gap:4, flexShrink:0}}>
                          <label style={{...S.fieldLabel, marginBottom:0}}>
                            Qty <span style={S.requiredStar}>*</span>
                            <span style={S.unitHint}>{p.unit}</span>
                          </label>
                          <div style={{display:'flex', alignItems:'center', gap:6}}>
                            <button
                              type="button"
                              title="Decrease"
                              onClick={() => setConfirmedProducts(cp => cp.map((x, j) => {
                                if (j !== i) return x
                                const next = Math.max(0, (parseFloat(x.quantity) || 0) - 1)
                                return {...x, quantity: String(next), _qtyAck: false}
                              }))}
                              style={{
                                width:40, height:40, borderRadius:8, background:'var(--surface)',
                                border:'1px solid var(--border)', color:'var(--text)', fontSize:20,
                                fontWeight:700, cursor:'pointer', display:'flex', alignItems:'center',
                                justifyContent:'center', flexShrink:0,
                              }}
                            >−</button>
                            <input
                              style={{...S.fieldInput, width:80, textAlign:'center', fontSize:18, fontWeight:700, fontFamily:'var(--font-head)', borderColor: missingQty ? 'var(--danger)' : showWarn ? '#E8A33D' : 'var(--border)'}}
                              type="number"
                              value={p.quantity}
                              placeholder="—"
                              onChange={e => setConfirmedProducts(cp => cp.map((x, j) => j === i ? {...x, quantity: e.target.value, _qtyAck: false} : x))}
                            />
                            <button
                              type="button"
                              title="Increase"
                              onClick={() => setConfirmedProducts(cp => cp.map((x, j) => {
                                if (j !== i) return x
                                const next = (parseFloat(x.quantity) || 0) + 1
                                return {...x, quantity: String(next), _qtyAck: false}
                              }))}
                              style={{
                                width:40, height:40, borderRadius:8, background:'var(--surface)',
                                border:'1px solid var(--border)', color:'var(--text)', fontSize:20,
                                fontWeight:700, cursor:'pointer', display:'flex', alignItems:'center',
                                justifyContent:'center', flexShrink:0,
                              }}
                            >+</button>
                            <span style={{
                              fontFamily:'var(--font-head)', fontWeight:700, fontSize:11, letterSpacing:1,
                              color:'var(--accent)', background:'rgba(27,158,212,.12)',
                              border:'1px solid rgba(27,158,212,.35)', borderRadius:6, padding:'4px 8px', flexShrink:0,
                            }}>{p.unit}</span>
                            <button
                              title="Remove this product"
                              onClick={() => setConfirmedProducts(cp => cp.filter((_, j) => j !== i))}
                              style={{
                                background: 'rgba(220,50,50,0.15)', border: '1px solid rgba(220,50,50,0.4)',
                                color: '#e55', borderRadius: 6, width: 32, height: 32,
                                fontSize: 16, cursor: 'pointer', display: 'flex',
                                alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                              }}
                            >✕</button>
                          </div>
                        </div>
                      </div>
                      {missingQty && (
                        <div style={{fontSize:11, color:'var(--danger)', marginTop:6, fontFamily:'var(--font-head)', letterSpacing:.5}}>
                          ⚠ Quantity required
                        </div>
                      )}
                      {showWarn && (
                        <div style={{marginTop:10, padding:'10px 12px', background:'rgba(232,163,61,.1)', border:'1px solid rgba(232,163,61,.35)', borderRadius:8}}>
                          <div style={{fontSize:12.5, color:'#e3c389', lineHeight:1.5, display:'flex', gap:6}}>
                            <span>⚠</span><span>{warn.msg}</span>
                          </div>
                          <div style={{display:'flex', gap:8, marginTop:8}}>
                            {warn.suggest != null && (
                              <button
                                onClick={() => setConfirmedProducts(cp => cp.map((x, j) => j === i ? {...x, quantity: String(warn.suggest), _qtyAck: true} : x))}
                                style={{
                                  background:'#E8A33D', color:'#1a1206', border:'none', borderRadius:6,
                                  padding:'8px 14px', fontFamily:'var(--font-head)', fontWeight:800,
                                  fontSize:12.5, letterSpacing:.5, cursor:'pointer',
                                }}
                              >USE {warn.suggest} {p.unit}</button>
                            )}
                            <button
                              onClick={() => setConfirmedProducts(cp => cp.map((x, j) => j === i ? {...x, _qtyAck: true} : x))}
                              style={{
                                background:'transparent', color:'var(--muted)', border:'1px solid var(--border)',
                                borderRadius:6, padding:'8px 14px', fontFamily:'var(--font-head)', fontWeight:700,
                                fontSize:12.5, letterSpacing:.5, cursor:'pointer',
                              }}
                            >KEEP AS-IS</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}

                <div style={S.field}>
                  <label style={S.fieldLabel}>Job Number <span style={S.requiredStar}>*</span></label>
                  <div ref={jobSearchRef} style={S.jobComboWrap}>
                    <input
                      style={{
                        ...S.jobComboInput,
                        borderColor: jobDropOpen ? 'var(--accent)' : (form.job ? 'var(--accent)' : 'var(--border)'),
                        borderRadius: jobDropOpen ? '6px 6px 0 0' : 6,
                      }}
                      placeholder="Type job # or name to search…"
                      value={jobSearch}
                      onChange={e => {
                        setJobSearch(e.target.value)
                        setForm(f => ({...f, job: ''}))
                        setJobDropOpen(true)
                      }}
                      onFocus={() => setJobDropOpen(true)}
                      autoComplete="off"
                    />
                    {jobDropOpen && (() => {
                      const q = jobSearch.toLowerCase()
                      const filtered = jobs.filter(j => j.toLowerCase().includes(q))
                      return filtered.length > 0 ? (
                        <div style={S.jobDropdown}>
                          {filtered.map(j => (
                            <div
                              key={j}
                              style={S.jobDropItem(false)}
                              onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.color = '#fff' }}
                              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text)' }}
                              onMouseDown={e => {
                                e.preventDefault()
                                setForm(f => ({...f, job: j}))
                                setJobSearch(j)
                                setJobDropOpen(false)
                              }}
                            >
                              {j}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={S.jobDropdown}>
                          <div style={{padding:'12px 14px', color:'var(--muted)', fontSize:13, fontFamily:'var(--font-head)', letterSpacing:1}}>NO MATCHES</div>
                        </div>
                      )
                    })()}
                  </div>
                  {form.job && (
                    <div style={{fontSize:12, color:'var(--accent)', marginTop:4, fontFamily:'var(--font-head)'}}>
                      ✓ {form.job}
                    </div>
                  )}
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

                {!canSubmit && (
                  <div style={{...S.missingWarning, background:'rgba(27,158,212,.08)', border:'1px solid rgba(27,158,212,.3)', color:'var(--muted)'}}>
                    All fields marked <span style={{color:'var(--danger)'}}>*</span> are required before saving
                  </div>
                )}

                {/* Tools matched from transcript */}
                {pendingTools.length > 0 && (
                  <div style={{marginBottom:16}}>
                    <div style={{fontFamily:'var(--font-head)', fontSize:11, fontWeight:700, letterSpacing:1.5, color:'var(--accent)', marginBottom:8}}>
                      🔧 TOOLS ALSO DETECTED — WILL BE LOGGED
                    </div>
                    {pendingTools.map((t, i) => (
                      <div key={i} style={{
                        background: 'var(--surface2)', borderRadius: 8, padding: '12px 16px',
                        marginBottom: 8, border: '1px solid var(--accent)',
                        display:'flex', justifyContent:'space-between', alignItems:'center', gap:12,
                      }}>
                        <div style={{display:'flex', alignItems:'center', gap:8, minWidth:0}}>
                          <span style={{fontSize:14}}>🔧</span>
                          <span style={{fontSize:13, color:'var(--text)'}}>{t.name}</span>
                        </div>
                        <div style={{display:'flex', flexDirection:'column', alignItems:'flex-end', gap:4, flexShrink:0}}>
                          <label style={{...S.fieldLabel, marginBottom:0}}>Qty</label>
                          <div style={{display:'flex', alignItems:'center', gap:6}}>
                            <input
                              style={{...S.fieldInput, width:70, textAlign:'right'}}
                              type="number"
                              min="1"
                              value={t.quantity}
                              placeholder="1"
                              onChange={e => setPendingTools(pt => pt.map((x, j) => j === i ? {...x, quantity: e.target.value} : x))}
                            />
                            <button
                              title="Remove this tool"
                              onClick={() => setPendingTools(pt => pt.filter((_,j) => j !== i))}
                              style={{
                                background: 'rgba(220,50,50,0.15)', border: '1px solid rgba(220,50,50,0.4)',
                                color: '#e55', borderRadius: 6, width: 32, height: 32,
                                fontSize: 16, cursor: 'pointer', display: 'flex',
                                alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                              }}
                            >✕</button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div style={S.btnRow}>
                  <button style={S.btnSecondary} onClick={resetCapture}>Cancel</button>
                  <button
                    style={S.btnPrimary(canSubmit)}
                    disabled={!canSubmit}
                    onClick={submitEntry}
                  >
                    {basket.length > 0 ? '+ Add to Basket (' + basket.length + ')' : 'Add to Basket'}
                  </button>
                </div>
              </div>
            )}

            {!processing && matchResult && !hasMatches && (
              pendingTools.length > 0 ? (
                // Tools-only result — no stock product needed
                <div style={S.cardAccent}>
                  <div style={S.titleAccent}>Confirm Tool Log</div>
                  <div style={{...S.hint, marginBottom: 16}}>
                    No stock products detected — only hand tools. Fill in the details below and save.
                  </div>

                  {/* Tools detected */}
                  <div style={{marginBottom:16}}>
                    <div style={{fontFamily:'var(--font-head)', fontSize:11, fontWeight:700, letterSpacing:1.5, color:'var(--accent)', marginBottom:8}}>
                      🔧 TOOLS DETECTED
                    </div>
                    {pendingTools.map((t, i) => (
                      <div key={i} style={{
                        background: 'var(--surface2)', borderRadius: 8, padding: '12px 16px',
                        marginBottom: 8, border: '1px solid var(--accent)',
                        display:'flex', justifyContent:'space-between', alignItems:'center', gap:12,
                      }}>
                        <div style={{display:'flex', alignItems:'center', gap:8, minWidth:0}}>
                          <span style={{fontSize:14}}>🔧</span>
                          <span style={{fontSize:13, color:'var(--text)'}}>{t.name}</span>
                        </div>
                        <div style={{display:'flex', flexDirection:'column', alignItems:'flex-end', gap:4, flexShrink:0}}>
                          <label style={{...S.fieldLabel, marginBottom:0}}>Qty</label>
                          <div style={{display:'flex', alignItems:'center', gap:6}}>
                            <input
                              style={{...S.fieldInput, width:70, textAlign:'right'}}
                              type="number"
                              min="1"
                              value={t.quantity}
                              placeholder="1"
                              onChange={e => setPendingTools(pt => pt.map((x, j) => j === i ? {...x, quantity: e.target.value} : x))}
                            />
                            <button
                              title="Remove this tool"
                              onClick={() => setPendingTools(pt => pt.filter((_,j) => j !== i))}
                              style={{
                                background: 'rgba(220,50,50,0.15)', border: '1px solid rgba(220,50,50,0.4)',
                                color: '#e55', borderRadius: 6, width: 32, height: 32,
                                fontSize: 16, cursor: 'pointer', display: 'flex',
                                alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                              }}
                            >✕</button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Job */}
                  <div style={S.field}>
                    <label style={S.fieldLabel}>Job Number <span style={S.requiredStar}>*</span></label>
                    <div ref={jobSearchRef} style={S.jobComboWrap}>
                      <input
                        style={{...S.jobComboInput, borderColor: jobDropOpen ? 'var(--accent)' : (form.job ? 'var(--accent)' : 'var(--border)'), borderRadius: jobDropOpen ? '6px 6px 0 0' : 6}}
                        placeholder="Type job # or name to search…"
                        value={jobSearch}
                        onChange={e => { setJobSearch(e.target.value); setForm(f => ({...f, job: ''})); setJobDropOpen(true) }}
                        onFocus={() => setJobDropOpen(true)}
                        autoComplete="off"
                      />
                      {jobDropOpen && (() => {
                        const q = jobSearch.toLowerCase()
                        const filtered = jobs.filter(j => j.toLowerCase().includes(q))
                        return filtered.length > 0 ? (
                          <div style={S.jobDropdown}>
                            {filtered.map(j => (
                              <div key={j} style={S.jobDropItem(false)}
                                onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.color = '#fff' }}
                                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text)' }}
                                onMouseDown={e => { e.preventDefault(); setForm(f => ({...f, job: j})); setJobSearch(j); setJobDropOpen(false) }}
                              >{j}</div>
                            ))}
                          </div>
                        ) : (
                          <div style={S.jobDropdown}>
                            <div style={{padding:'12px 14px', color:'var(--muted)', fontSize:13, fontFamily:'var(--font-head)', letterSpacing:1}}>NO MATCHES</div>
                          </div>
                        )
                      })()}
                    </div>
                    {form.job && <div style={{fontSize:12, color:'var(--accent)', marginTop:4, fontFamily:'var(--font-head)'}}>✓ {form.job}</div>}
                  </div>

                  {/* Worker name */}
                  <div style={S.field}>
                    <label style={S.fieldLabel}>Worker Name <span style={S.requiredStar}>*</span></label>
                    <input
                      style={S.fieldInput}
                      value={form.worker_name}
                      onChange={e => setForm(f => ({...f, worker_name: e.target.value}))}
                      placeholder="e.g. Dave Smith"
                    />
                  </div>

                  <div style={S.btnRow}>
                    <button style={S.btnSecondary} onClick={resetCapture}>Cancel</button>
                    <button
                      style={S.btnPrimary(!!(form.job.trim() && form.worker_name.trim() && pendingTools.length > 0))}
                      disabled={!(form.job.trim() && form.worker_name.trim() && pendingTools.length > 0)}
                      onClick={async () => {
                        try {
                          for (const tool of pendingTools) {
                            const qty = parseInt(tool.quantity) || 1
                            await fetch('/api/tool-entries', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ tool_name: tool.name, job: form.job, worker_name: form.worker_name, quantity: qty, source: inputMode }),
                            })
                          }
                          if (!basketJob && form.job) { setBasketJob(form.job); setBasketJobSearch(form.job) }
                          if (!basketWorker && form.worker_name) setBasketWorker(form.worker_name)
                          showToast(`${pendingTools.length} tool${pendingTools.length > 1 ? 's' : ''} logged ✓`)
                          loadToolEntries()
                          setTranscript(''); setTextInput(''); setMatchResult(null); setPendingTools([])
                          setForm(f => ({ ...f, quantity: '' }))
                        } catch { showToast('Save failed — try again') }
                      }}
                    >
                      Log Tools ✓
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{...S.card, border:'1px solid var(--danger)'}}>
                  <div style={{color:'var(--danger)', fontFamily:'var(--font-head)', fontWeight:700, fontSize:16, marginBottom:8}}>No product matched</div>
                  <div style={{color:'var(--muted)', fontSize:14, marginBottom:16}}>
                    Try again with a different product name or description.
                  </div>
                  <button style={S.btnSecondary} onClick={resetCapture}>Try again</button>
                </div>
              )
            )}

            {/* ── BASKET PANEL ─────────────────────────────── */}
            {basket.length > 0 && (
              <div style={{...S.card, border:'2px solid var(--accent)', marginTop:8}}>
                <div style={{...S.titleAccent, marginBottom:12}}>
                  🧺 Basket — {basket.length} item{basket.length > 1 ? 's' : ''} logged
                </div>
                <div style={{marginBottom:16}}>
                  {basket.map((item, i) => (
                    <div key={i} style={{
                      display:'flex', alignItems:'center', justifyContent:'space-between',
                      padding:'10px 14px', background:'var(--surface2)',
                      borderRadius:8, marginBottom:6,
                      border: `1px solid ${item.type === 'tool' ? 'rgba(27,158,212,.35)' : 'var(--border)'}`,
                    }}>
                      <div style={{display:'flex', alignItems:'center', gap:8}}>
                        {item.type === 'tool' ? (
                          <>
                            <span style={{fontSize:14}}>🔧</span>
                            <span style={{fontSize:13, color:'var(--text)'}}>{item.toolName}</span>
                          </>
                        ) : (
                          <>
                            <span style={{fontFamily:'var(--font-head)', fontWeight:700, color:'var(--accent)', fontSize:12, marginRight:4}}>
                              {item.product.code}
                            </span>
                            <span style={{fontSize:13, color:'var(--text)'}}>{item.product.description}</span>
                          </>
                        )}
                      </div>
                      <div style={{display:'flex', alignItems:'center', gap:10}}>
                        {item.type === 'stock' ? (
                          <span style={{fontFamily:'var(--font-head)', fontWeight:700, fontSize:13}}>
                            ×{item.quantity}<span style={{fontSize:10, color:'var(--muted)', marginLeft:2}}>{item.product.unit}</span>
                          </span>
                        ) : (
                          <span style={{fontFamily:'var(--font-head)', fontWeight:700, fontSize:13}}>
                            ×{item.quantity}
                          </span>
                        )}
                        <button
                          style={{background:'transparent', border:'none', color:'var(--muted)', cursor:'pointer', fontSize:16, padding:'0 4px'}}
                          onClick={() => setBasket(b => b.filter((_,j) => j !== i))}
                          title="Remove"
                        >✕</button>
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{display:'flex', gap:12, marginBottom:16, flexWrap:'wrap'}}>
                  <div style={{flex:1, minWidth:180}}>
                    <label style={S.fieldLabel}>Job <span style={S.requiredStar}>*</span></label>
                    <div ref={basketJobSearchRef} style={S.jobComboWrap}>
                      <input
                        style={{
                          ...S.jobComboInput, fontSize:13,
                          borderColor: basketJobDropOpen ? 'var(--accent)' : (basketJob ? 'var(--accent)' : 'var(--border)'),
                          borderRadius: basketJobDropOpen ? '6px 6px 0 0' : 6,
                        }}
                        placeholder="Type job # or name…"
                        value={basketJobSearch}
                        onChange={e => { setBasketJobSearch(e.target.value); setBasketJob(''); setBasketJobDropOpen(true) }}
                        onFocus={() => setBasketJobDropOpen(true)}
                        autoComplete="off"
                      />
                      {basketJobDropOpen && (() => {
                        const q = basketJobSearch.toLowerCase()
                        const filtered = jobs.filter(j => j.toLowerCase().includes(q))
                        return filtered.length > 0 ? (
                          <div style={S.jobDropdown}>
                            {filtered.map(j => (
                              <div key={j} style={S.jobDropItem(false)}
                                onMouseEnter={e => { e.currentTarget.style.background='var(--accent)'; e.currentTarget.style.color='#fff' }}
                                onMouseLeave={e => { e.currentTarget.style.background='transparent'; e.currentTarget.style.color='var(--text)' }}
                                onMouseDown={e => { e.preventDefault(); setBasketJob(j); setBasketJobSearch(j); setBasketJobDropOpen(false) }}
                              >{j}</div>
                            ))}
                          </div>
                        ) : (
                          <div style={S.jobDropdown}>
                            <div style={{padding:'10px 14px', color:'var(--muted)', fontSize:12, fontFamily:'var(--font-head)', letterSpacing:1}}>NO MATCHES</div>
                          </div>
                        )
                      })()}
                    </div>
                  </div>
                  <div style={{flex:1, minWidth:140}}>
                    <label style={S.fieldLabel}>Worker <span style={S.requiredStar}>*</span></label>
                    <input
                      style={{...S.fieldInput, fontSize:13}}
                      placeholder="e.g. Dave Smith"
                      value={basketWorker}
                      onChange={e => setBasketWorker(e.target.value)}
                    />
                  </div>
                </div>
                <div style={{fontSize:12, color:'var(--muted)', marginBottom:12}}>
                  All items above are already saved to their respective logs. Tap <strong style={{color:'var(--text)'}}>Done</strong> to clear and start fresh.
                </div>
                <div style={{display:'flex', gap:10}}>
                  <button style={S.btnSecondary} onClick={resetCapture}>Clear All</button>
                  <button style={{...S.btnPrimary(true), flex:1}} onClick={submitBasketAll}>✓ Done — Clear Basket</button>
                </div>
              </div>
            )}
          </>
        )}

        {/* ── LOG TAB ──────────────────────────────────────────────── */}
        {tab === 'log' && (
          <div style={S.logCard}>
            <div style={S.logHeader}>
              {/* Stock / Tools sub-tab toggle */}
              <div style={{display:'flex', gap:0, marginBottom:16, borderRadius:6, overflow:'hidden', border:'1px solid var(--border)', width:'fit-content'}}>
                {[['stock','📦 Stock'],['tools','🔧 Tools']].map(([t,label]) => (
                  <button key={t} onClick={() => setLogTab(t)} style={{
                    padding:'7px 20px', background: logTab===t ? 'var(--accent)' : 'transparent',
                    color: logTab===t ? '#fff' : 'var(--muted)', border:'none',
                    fontFamily:'var(--font-head)', fontWeight:700, fontSize:13, letterSpacing:1,
                    textTransform:'uppercase', cursor:'pointer', transition:'all .15s',
                  }}>{label}</button>
                ))}
              </div>

              <div style={S.logTitleRow}>
                <div style={S.logTitle}>
                  {logTab === 'stock' ? `Stock Entries (${entries.length})` : `Tool Entries (${toolEntries.length})`}
                </div>
                <button style={S.exportBtn} onClick={() => {
                  const url = logTab === 'stock' ? buildExportUrl() : buildToolExportUrl()
                  window.open(url, '_blank')
                }}>↓ Export CSV</button>
              </div>

              <div style={S.exportControls}>
                <span style={S.dateLabel}>Export range:</span>
                <div style={{display:'flex', alignItems:'center', gap:6}}>
                  <span style={{fontSize:12, color:'var(--muted)'}}>From</span>
                  <input type="date" style={S.dateInput} value={exportFrom} onChange={e => setExportFrom(e.target.value)} />
                </div>
                <div style={{display:'flex', alignItems:'center', gap:6}}>
                  <span style={{fontSize:12, color:'var(--muted)'}}>To</span>
                  <input type="date" style={S.dateInput} value={exportTo} onChange={e => setExportTo(e.target.value)} />
                </div>
                {(exportFrom || exportTo) && (
                  <button style={{...S.exportBtn, background:'transparent', color:'var(--muted)', border:'1px solid var(--border)'}}
                    onClick={() => { setExportFrom(''); setExportTo('') }}>Clear</button>
                )}
              </div>
              {(exportFrom || exportTo) && (
                <div style={{fontSize:12, color:'var(--accent)', marginTop:8, fontFamily:'var(--font-head)', letterSpacing:.5}}>
                  ↑ Export will include only entries{exportFrom ? ` from ${exportFrom}` : ''}{exportTo ? ` to ${exportTo}` : ''}
                </div>
              )}
            </div>

            {/* ── STOCK SUB-TAB ── */}
            {logTab === 'stock' && (
              entries.length === 0 ? (
                <div style={S.empty}>No stock entries yet</div>
              ) : (
                <>
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
                        <div style={{color:'var(--text)',fontSize:12,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}} title={e.job}>{e.job}</div>
                        <div style={{fontFamily:'var(--font-head)',fontWeight:700,fontSize:13}}>
                          {e.cost_quantity}<span style={{fontSize:10,color:'var(--muted)',marginLeft:2}}>{e.unit}</span>
                        </div>
                        <div style={{color:'var(--muted)',fontSize:12,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}} title={e.worker_name}>
                          {e.source && <span title={e.source === 'voice' ? 'Voice entry' : 'Typed entry'} style={{fontSize:11,flexShrink:0}}>{e.source === 'voice' ? '🎤' : '⌨️'}</span>}
                          <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{e.worker_name || '—'}</span>
                        </div>
                        <button
                          style={{padding:'4px 8px', background:'transparent', color:'var(--accent)', fontSize:14, borderRadius:4, border:'1px solid transparent', cursor:'pointer'}}
                          onClick={() => { setEditingEntry(e); setEditForm({ job: e.job, cost_quantity: e.cost_quantity, worker_name: e.worker_name || '' }); setEditJobSearch(e.job || ''); setEditJobDropOpen(false) }}
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
                              <div ref={editJobSearchRef} style={S.jobComboWrap}>
                                <input
                                  style={{...S.jobComboInput, fontSize:13,
                                    borderColor: editJobDropOpen ? 'var(--accent)' : (editForm.job ? 'var(--accent)' : 'var(--border)'),
                                    borderRadius: editJobDropOpen ? '6px 6px 0 0' : 6,
                                  }}
                                  placeholder="Type to search…"
                                  value={editJobSearch || editForm.job || ''}
                                  onChange={ev => { setEditJobSearch(ev.target.value); setEditForm(f => ({...f, job: ''})); setEditJobDropOpen(true) }}
                                  onFocus={() => { setEditJobSearch(editForm.job || ''); setEditJobDropOpen(true) }}
                                  autoComplete="off"
                                />
                                {editJobDropOpen && (() => {
                                  const q = (editJobSearch || '').toLowerCase()
                                  const filtered = jobs.filter(j => j.toLowerCase().includes(q))
                                  return filtered.length > 0 ? (
                                    <div style={S.jobDropdown}>
                                      {filtered.map(j => (
                                        <div key={j} style={S.jobDropItem(false)}
                                          onMouseEnter={e => { e.currentTarget.style.background='var(--accent)'; e.currentTarget.style.color='#fff' }}
                                          onMouseLeave={e => { e.currentTarget.style.background='transparent'; e.currentTarget.style.color='var(--text)' }}
                                          onMouseDown={ev => { ev.preventDefault(); setEditForm(f => ({...f, job: j})); setEditJobSearch(j); setEditJobDropOpen(false) }}
                                        >{j}</div>
                                      ))}
                                    </div>
                                  ) : (
                                    <div style={S.jobDropdown}><div style={{padding:'10px 14px', color:'var(--muted)', fontSize:12, fontFamily:'var(--font-head)', letterSpacing:1}}>NO MATCHES</div></div>
                                  )
                                })()}
                              </div>
                            </div>
                            <div>
                              <label style={S.fieldLabel}>Qty <span style={S.requiredStar}>*</span></label>
                              <input type="number" style={{...S.fieldInput, fontSize:13}} value={editForm.cost_quantity} onChange={ev => setEditForm(f => ({...f, cost_quantity: ev.target.value}))} />
                            </div>
                            <div>
                              <label style={S.fieldLabel}>Worker</label>
                              <input style={{...S.fieldInput, fontSize:13}} value={editForm.worker_name} onChange={ev => setEditForm(f => ({...f, worker_name: ev.target.value}))} />
                            </div>
                          </div>
                          <div style={{display:'flex', gap:8}}>
                            <button style={{...S.btnPrimary(true), flex:'none', padding:'8px 20px', fontSize:13}} onClick={saveEditEntry}>Save</button>
                            <button style={{...S.btnSecondary, padding:'8px 16px', fontSize:13}} onClick={() => { setEditingEntry(null); setEditJobSearch(''); setEditJobDropOpen(false) }}>Cancel</button>
                          </div>
                        </div>
                      )}
                    </React.Fragment>
                  ))}
                </>
              )
            )}

            {/* ── TOOLS SUB-TAB ── */}
            {logTab === 'tools' && (
              toolEntries.length === 0 ? (
                <div style={S.empty}>No tool entries yet</div>
              ) : (() => {
                const toolCostMap = Object.fromEntries(handTools.map(t => [t.name.toLowerCase(), t.cost]))
                const getUnitCost = name => toolCostMap[name?.toLowerCase()] ?? null
                const totalCost = toolEntries.reduce((sum, e) => {
                  const c = getUnitCost(e.tool_name)
                  return c != null ? sum + c * (e.quantity ?? 1) : sum
                }, 0)
                return (
                  <>
                    <div style={{
                      display:'grid', gridTemplateColumns:'1fr 50px 70px 70px 80px 160px 100px 36px 36px',
                      gap:8, padding:'10px 20px', borderBottom:'2px solid var(--border)', alignItems:'center',
                    }}>
                      {['Tool','Qty','Unit $','Total $','Date','Job','Worker','',''].map((h,i) => <div key={i} style={S.logHead}>{h}</div>)}
                    </div>
                    {toolEntries.map(e => {
                      const unitCost = getUnitCost(e.tool_name)
                      const qty = e.quantity ?? 1
                      const lineTotal = unitCost != null ? unitCost * qty : null
                      return (
                        <React.Fragment key={e.id}>
                          <div style={{
                            display:'grid', gridTemplateColumns:'1fr 50px 70px 70px 80px 160px 100px 36px 36px',
                            gap:8, padding:'11px 20px', borderBottom:'1px solid var(--border)', alignItems:'center', fontSize:13,
                          }}>
                            <div style={{color:'var(--text)', display:'flex', alignItems:'center', gap:6}}>
                              <span>🔧</span>{e.tool_name}
                            </div>
                            <div style={{color:'var(--accent)', fontFamily:'var(--font-head)', fontWeight:700}}>{qty}</div>
                            <div style={{color:'var(--muted)',fontSize:12}}>{unitCost != null ? `$${unitCost}` : '—'}</div>
                            <div style={{color:'var(--text)',fontSize:12,fontFamily:'var(--font-head)',fontWeight:600}}>{lineTotal != null ? `$${lineTotal}` : '—'}</div>
                            <div style={{color:'var(--muted)',fontSize:12}}>{String(e.entry_date).slice(0,10)}</div>
                            <div style={{color:'var(--text)',fontSize:12,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}} title={e.job}>{e.job}</div>
                            <div style={{color:'var(--muted)',fontSize:12,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:5}}>
                              {e.source && <span title={e.source === 'voice' ? 'Voice entry' : 'Typed entry'} style={{fontSize:11,flexShrink:0}}>{e.source === 'voice' ? '🎤' : '⌨️'}</span>}
                              <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{e.worker_name || '—'}</span>
                            </div>
                            <button
                              style={{padding:'4px 8px', background:'transparent', color:'var(--accent)', fontSize:14, borderRadius:4, border:'1px solid transparent', cursor:'pointer'}}
                              onClick={() => { setEditingToolEntry(e); setEditToolForm({ job: e.job, quantity: qty, worker_name: e.worker_name || '' }); setEditToolJobSearch(e.job || ''); setEditToolJobDropOpen(false) }}
                              title="Edit"
                            >✎</button>
                            <button style={S.deleteBtn} onClick={() => deleteToolEntry(e.id)} title="Delete">✕</button>
                          </div>
                          {editingToolEntry?.id === e.id && (
                            <div style={{gridColumn:'1/-1', background:'var(--surface2)', border:'1px solid var(--accent)', borderRadius:8, padding:'16px 20px', margin:'0 0 4px 0'}}>
                              <div style={{fontFamily:'var(--font-head)', fontSize:13, fontWeight:700, color:'var(--accent)', letterSpacing:1, marginBottom:12}}>
                                EDITING: 🔧 {e.tool_name}
                              </div>
                              <div style={{display:'grid', gridTemplateColumns:'1fr 100px 1fr', gap:12, marginBottom:12}}>
                                <div>
                                  <label style={S.fieldLabel}>Job <span style={S.requiredStar}>*</span></label>
                                  <div ref={editToolJobSearchRef} style={S.jobComboWrap}>
                                    <input
                                      style={{...S.jobComboInput, fontSize:13,
                                        borderColor: editToolJobDropOpen ? 'var(--accent)' : (editToolForm.job ? 'var(--accent)' : 'var(--border)'),
                                        borderRadius: editToolJobDropOpen ? '6px 6px 0 0' : 6,
                                      }}
                                      placeholder="Type to search…"
                                      value={editToolJobSearch || editToolForm.job || ''}
                                      onChange={ev => { setEditToolJobSearch(ev.target.value); setEditToolForm(f => ({...f, job: ''})); setEditToolJobDropOpen(true) }}
                                      onFocus={() => { setEditToolJobSearch(editToolForm.job || ''); setEditToolJobDropOpen(true) }}
                                      autoComplete="off"
                                    />
                                    {editToolJobDropOpen && (() => {
                                      const q = (editToolJobSearch || '').toLowerCase()
                                      const filtered = jobs.filter(j => j.toLowerCase().includes(q))
                                      return filtered.length > 0 ? (
                                        <div style={S.jobDropdown}>
                                          {filtered.map(j => (
                                            <div key={j} style={S.jobDropItem(false)}
                                              onMouseEnter={ev => { ev.currentTarget.style.background='var(--accent)'; ev.currentTarget.style.color='#fff' }}
                                              onMouseLeave={ev => { ev.currentTarget.style.background='transparent'; ev.currentTarget.style.color='var(--text)' }}
                                              onMouseDown={ev => { ev.preventDefault(); setEditToolForm(f => ({...f, job: j})); setEditToolJobSearch(j); setEditToolJobDropOpen(false) }}
                                            >{j}</div>
                                          ))}
                                        </div>
                                      ) : (
                                        <div style={S.jobDropdown}><div style={{padding:'10px 14px', color:'var(--muted)', fontSize:12, fontFamily:'var(--font-head)', letterSpacing:1}}>NO MATCHES</div></div>
                                      )
                                    })()}
                                  </div>
                                </div>
                                <div>
                                  <label style={S.fieldLabel}>Qty <span style={S.requiredStar}>*</span></label>
                                  <input type="number" min="1" style={{...S.fieldInput, fontSize:13}} value={editToolForm.quantity} onChange={ev => setEditToolForm(f => ({...f, quantity: ev.target.value}))} />
                                </div>
                                <div>
                                  <label style={S.fieldLabel}>Worker</label>
                                  <input style={{...S.fieldInput, fontSize:13}} value={editToolForm.worker_name} onChange={ev => setEditToolForm(f => ({...f, worker_name: ev.target.value}))} />
                                </div>
                              </div>
                              <div style={{display:'flex', gap:8}}>
                                <button style={{...S.btnPrimary(true), flex:'none', padding:'8px 20px', fontSize:13}} onClick={saveEditToolEntry}>Save</button>
                                <button style={{...S.btnSecondary, padding:'8px 16px', fontSize:13}} onClick={() => { setEditingToolEntry(null); setEditToolJobSearch(''); setEditToolJobDropOpen(false) }}>Cancel</button>
                              </div>
                            </div>
                          )}
                        </React.Fragment>
                      )
                    })}
                    {totalCost > 0 && (
                      <div style={{
                        display:'flex', justifyContent:'flex-end', alignItems:'center',
                        padding:'12px 20px', borderTop:'2px solid var(--border)',
                        gap:12, background:'var(--surface2)',
                      }}>
                        <span style={{color:'var(--muted)', fontSize:12, fontFamily:'var(--font-head)', letterSpacing:1, textTransform:'uppercase'}}>Total Tool Value</span>
                        <span style={{color:'var(--accent)', fontFamily:'var(--font-head)', fontSize:18, fontWeight:800}}>${totalCost.toLocaleString()}</span>
                      </div>
                    )}
                  </>
                )
              })()
            )}
          </div>
        )}

        {/* ── DAY WORKS TAB ────────────────────────────────────────── */}
        {tab === 'dayworks' && (() => {
          const dwIdx = DW_TABS.findIndex(t => t.id === dwActiveTab)
          const dwDetailsDone = !!dwJob && !!dwVariation && (dwVariation !== 'Yes' || !!dwVoNumber)
          const dwLabourDone = dwLabourRows.length > 0
          const dwMaterialsDone = dwMaterialRows.length > 0
          const dwCommentsDone = dwComments.trim().length > 0 || dwPhotos.length > 0
          const dwSignoffDone = dwSignoffMode === 'glass' ? dwSigned : !!dwClientEmail
          const dwDoneMap = { details: dwDetailsDone, labour: dwLabourDone, materials: dwMaterialsDone, comments: dwCommentsDone, signoff: dwSignoffDone }
          const dwIsLastTab = dwIdx === DW_TABS.length - 1
          const dwProgressPct = (dwIdx / (DW_TABS.length - 1)) * 100
          const dwQ = dwJobSearch.toLowerCase()
          const dwJobMatches = jobs.filter(j => j.toLowerCase().includes(dwQ))
          const dwJobNumber = (dwJob.split(' - ')[0] || '').trim()
          const dwJobVos = vos.filter(v => v.job === dwJobNumber)

          const dwFilteredLog = dwEntries.filter(e => {
            if (dwFilterJob && !e.job.toLowerCase().includes(dwFilterJob.toLowerCase())) return false
            if (dwFilterVariation !== 'all' && e.variation !== dwFilterVariation) return false
            if (dwFilterStatus !== 'all' && e.status !== dwFilterStatus) return false
            return true
          })

          return (
          <div>
            <div style={S.dwToggle}>
              <button style={S.dwToggleBtn(dwView==='new')} onClick={() => setDwView('new')}>New Sheet</button>
              <button style={S.dwToggleBtn(dwView==='log')} onClick={() => { setDwView('log'); loadDayworksEntries() }}>Log ({dwEntries.length})</button>
            </div>

            {dwView === 'new' && dwStep === 'form' && (
              <div style={S.logCard}>
                <div style={{padding:'16px 18px 0', borderBottom:'2px solid var(--accent)'}}>
                  <div>
                    <div style={{fontFamily:'var(--font-head)', fontSize:20, fontWeight:800, letterSpacing:.3, color:'var(--text)'}}>{dwJob || 'New Day Works Sheet'}</div>
                    <div style={{display:'flex', alignItems:'center', gap:8, marginTop:2}}>
                      <span style={{fontFamily:'var(--font-head)', fontSize:11, fontWeight:700, letterSpacing:1.5, color:'var(--muted)', textTransform:'uppercase'}}>Day Works</span>
                      {dwVariation === 'Yes' && dwVoNumber && <span style={{fontFamily:'var(--font-head)', fontSize:12, fontWeight:700, color:'var(--accent)'}}>{dwVoNumber}</span>}
                    </div>
                  </div>
                  <div style={{marginTop:14, paddingBottom:10}}>
                    <div style={S.dwProgressTrack}><div style={S.dwProgressFill(dwProgressPct)} /></div>
                    <div style={S.dwTabRow}>
                      {DW_TABS.map((t, i) => (
                        <button key={t.id} onClick={() => dwSetTab(t.id)} style={S.dwTabBtn(dwActiveTab === t.id)}>
                          <span style={S.dwTabBadge(dwDoneMap[t.id], dwActiveTab === t.id)}>{dwDoneMap[t.id] ? '✓' : i + 1}</span>
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {(dwActiveTab === 'labour' || dwActiveTab === 'materials') && (() => {
                  return (
                    <div style={S.dwCaptureWrap}>
                      <div style={{...S.modeToggle, margin:'0 auto 12px'}}>
                        {[['voice','Voice'],['text','Text']].map(([m,label]) => (
                          <button key={m} style={S.modeBtn(dwInputMode===m)} onClick={() => setDwInputMode(m)}>{label}</button>
                        ))}
                      </div>

                      {dwInputMode === 'voice' ? (
                        <div style={{display:'flex', flexDirection:'column', alignItems:'center', gap:10}}>
                          <button style={S.dwMicBtn(dwListening)} onClick={dwToggleListen}>{dwListening ? '⏹' : '🎤'}</button>
                          <div style={{fontFamily:'var(--font-head)', fontSize:11, fontWeight:700, letterSpacing:1, textTransform:'uppercase', color:'var(--muted)'}}>
                            {dwListening ? 'Listening…' : 'Tap to speak'}
                          </div>
                          <div style={S.dwCaptureDisplay}>{dwCaptureText || 'Transcript will appear here'}</div>
                        </div>
                      ) : (
                        <div style={S.dwCaptureBar}>
                          <input
                            value={dwCaptureText}
                            onChange={e => setDwCaptureText(e.target.value)}
                            onKeyDown={dwOnCaptureKeyDown}
                            placeholder="Type here…"
                            style={{flex:1, border:'none', outline:'none', fontSize:13.5, background:'transparent', color:'var(--text)'}}
                          />
                          <button onClick={() => dwOnCaptureSubmit()} style={{border:'none', background:'var(--accent)', color:'#fff', borderRadius:6, padding:'8px 14px', fontFamily:'var(--font-head)', fontSize:12, fontWeight:700, letterSpacing:.5, textTransform:'uppercase', cursor:'pointer'}}>Add</button>
                        </div>
                      )}

                      {dwLastParsed && (
                        <div style={S.dwLastParsed}>
                          <span>{dwLastParsed.summary}</span>
                          <button onClick={dwUndoLast} style={{border:'none', background:'none', color:'var(--text)', fontWeight:700, cursor:'pointer', fontSize:12.5, fontFamily:'var(--font-head)', letterSpacing:.5, textTransform:'uppercase'}}>
                            {dwLastParsed.type === 'labour' || dwLastParsed.type === 'material' ? 'Undo' : 'Dismiss'}
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })()}

                {dwActiveTab === 'details' && (
                  <div style={{padding:'20px 18px 32px', display:'flex', flexDirection:'column', gap:18}}>
                    <div style={S.dwFieldWrap}>
                      <label style={S.fieldLabel}>Job Name and Number <span style={S.requiredStar}>*</span></label>
                      <div ref={dwJobSearchRef} style={S.jobComboWrap}>
                        <input
                          style={{...S.jobComboInput, borderColor: dwJobDropOpen ? 'var(--accent)' : (dwJob ? 'var(--accent)' : 'var(--border)'), borderRadius: dwJobDropOpen ? '6px 6px 0 0' : 6}}
                          placeholder="Type job # or name to search…"
                          value={dwJobSearch}
                          onChange={e => { setDwJobSearch(e.target.value); setDwJob(e.target.value); setDwJobDropOpen(true) }}
                          onFocus={() => setDwJobDropOpen(true)}
                          autoComplete="off"
                        />
                        {dwJobDropOpen && dwJobMatches.length > 0 && (
                          <div style={S.jobDropdown}>
                            {dwJobMatches.map(j => (
                              <div key={j} style={S.jobDropItem(false)}
                                onMouseEnter={e => { e.currentTarget.style.background='var(--accent)'; e.currentTarget.style.color='#fff' }}
                                onMouseLeave={e => { e.currentTarget.style.background='transparent'; e.currentTarget.style.color='var(--text)' }}
                                onMouseDown={e => { e.preventDefault(); setDwJob(j); setDwJobSearch(j); setDwJobDropOpen(false) }}
                              >{j}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={S.dwFieldWrap}>
                      <label style={S.fieldLabel}>Date <span style={S.requiredStar}>*</span></label>
                      <input type="date" value={dwDate} onChange={e => setDwDate(e.target.value)} style={S.fieldInput} />
                    </div>
                    <div style={S.dwFieldWrap}>
                      <label style={S.fieldLabel}>Variation Work? <span style={S.requiredStar}>*</span></label>
                      <div style={S.dwYesNo}>
                        <button style={S.dwYesNoBtn(dwVariation==='Yes', true)} onClick={() => setDwVariation('Yes')}>Yes</button>
                        <button style={S.dwYesNoBtn(dwVariation==='No', false)} onClick={() => { setDwVariation('No'); setDwVoNumber('') }}>No</button>
                      </div>
                    </div>
                    {dwVariation === 'Yes' && (
                      <div style={S.dwFieldWrap}>
                        <label style={S.fieldLabel}>Variation Number <span style={S.requiredStar}>*</span></label>
                        {dwJobVos.length > 0 ? (
                          <select value={dwVoNumber} onChange={e => setDwVoNumber(e.target.value)} style={S.fieldSelect}>
                            <option value="">Select a VO number</option>
                            {dwJobVos.map(v => (
                              <option key={v.vo} value={v.vo}>{v.vo}{v.description ? ` — ${v.description}` : ''}</option>
                            ))}
                          </select>
                        ) : (
                          <>
                            <input value={dwVoNumber} onChange={e => setDwVoNumber(e.target.value)} placeholder="e.g. VO001" style={S.fieldInput} />
                            <div style={{fontSize:11.5, color:'var(--muted)', marginTop:4}}>No VOs on file for this job yet — enter the number manually</div>
                          </>
                        )}
                      </div>
                    )}
                    <div style={S.dwFieldWrap}>
                      <label style={S.fieldLabel}>Location / Grid Ref</label>
                      <input value={dwLocation} onChange={e => setDwLocation(e.target.value)} placeholder="e.g. Zone 4 / Level 4 Unit A · Grid C7" style={S.fieldInput} />
                    </div>
                  </div>
                )}

                {dwActiveTab === 'labour' && (
                  <div style={S.dwSection}>
                    <div style={S.dwSectionHead}>
                      <div style={S.dwSectionTitle}>Labour Hours</div>
                      <div style={{fontSize:13, color:'var(--muted)'}}>{dwLabourRows.length} / 40</div>
                    </div>
                    {dwLabourRows.length === 0 ? (
                      <div style={S.dwRowEmpty}>No workers logged yet — use voice/text above, e.g. "Steve worked 9:30am to 6pm on formwork"</div>
                    ) : dwLabourRows.map(row => (
                      <div key={row.id} style={S.dwRow}>
                        <div>
                          <div style={{fontSize:14.5, fontWeight:600, color:'var(--text)'}}>{row.name}</div>
                          <div style={{fontSize:12.5, color:'var(--muted)', marginTop:2}}>{row.activity} · {row.start}–{row.end}</div>
                        </div>
                        <div style={{display:'flex', alignItems:'center', gap:10}}>
                          <div style={{fontFamily:'var(--font-head)', fontSize:15, fontWeight:700, color:'var(--accent)'}}>{row.hoursLabel}</div>
                          <button onClick={() => dwDeleteLabourRow(row.id)} style={{border:'none', background:'none', color:'var(--danger)', fontSize:15, cursor:'pointer'}}>✕</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {dwActiveTab === 'materials' && (
                  <div style={S.dwSection}>
                    <div style={S.dwSectionHead}>
                      <div style={S.dwSectionTitle}>Materials</div>
                      <div style={{fontSize:13, color:'var(--muted)'}}>{dwMaterialRows.length} / 24</div>
                    </div>
                    {dwMaterialRows.length === 0 ? (
                      <div style={S.dwRowEmpty}>No materials logged yet — try "50 bags of cement" or "10 metres of pipe"</div>
                    ) : dwMaterialRows.map(row => (
                      <div key={row.id} style={S.dwRow}>
                        <div>
                          <div style={{fontSize:14.5, fontWeight:600, color:'var(--text)'}}>{row.item}</div>
                          <div style={{fontSize:12.5, color:'var(--muted)', marginTop:2}}>Unit: {row.unit}</div>
                        </div>
                        <div style={{display:'flex', alignItems:'center', gap:10}}>
                          <div style={{fontFamily:'var(--font-head)', fontSize:15, fontWeight:700, color:'var(--accent)'}}>{row.qty}</div>
                          <button onClick={() => dwDeleteMaterialRow(row.id)} style={{border:'none', background:'none', color:'var(--danger)', fontSize:15, cursor:'pointer'}}>✕</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {dwActiveTab === 'comments' && (
                  <div style={S.dwSectionPad}>
                    <div style={S.dwSectionTitle}>Any other comments</div>
                    <textarea value={dwComments} onChange={e => setDwComments(e.target.value)} placeholder="Notes on access, delays, safety, anything worth flagging..." style={{width:'100%', minHeight:100, border:'1px solid var(--border)', background:'var(--surface2)', borderRadius:8, padding:12, fontSize:14, color:'var(--text)', resize:'vertical'}} />
                    <div style={{display:'flex', alignItems:'center', gap:10}}>
                      <button onClick={dwOpenCamera} style={{display:'flex', alignItems:'center', gap:8, border:'1px solid var(--accent)', color:'var(--accent)', background:'rgba(27,158,212,.08)', borderRadius:6, padding:'9px 14px', fontFamily:'var(--font-head)', fontSize:13, fontWeight:700, letterSpacing:.5, textTransform:'uppercase', cursor:'pointer'}}>📷 Add Photo</button>
                      <span style={{fontSize:12.5, color:'var(--muted)'}}>{dwPhotos.length} attached</span>
                    </div>
                    <input ref={dwFileInputRef} onChange={dwOnFilesSelected} type="file" accept="image/*" capture="environment" multiple style={{display:'none'}} />
                    {dwPhotos.length > 0 && (
                      <div style={{display:'flex', flexWrap:'wrap', gap:10}}>
                        {dwPhotos.map(p => (
                          <div key={p.id} style={{position:'relative', width:72, height:72, borderRadius:8, overflow:'hidden', border:'1px solid var(--border)'}}>
                            <img src={p.src} style={{width:'100%', height:'100%', objectFit:'cover'}} />
                            <button onClick={() => dwRemovePhoto(p.id)} style={{position:'absolute', top:2, right:2, width:18, height:18, borderRadius:'50%', border:'none', background:'rgba(0,0,0,.7)', color:'#fff', fontSize:11, lineHeight:'18px', cursor:'pointer', padding:0}}>✕</button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {dwActiveTab === 'signoff' && (
                  <div style={S.dwSectionPad}>
                    <div>
                      <div style={S.dwSectionTitle}>Client Sign-off</div>
                      <div style={{fontSize:12.5, color:'var(--muted)', marginTop:2}}>This dayworks sheet must be signed by the client to confirm the work above</div>
                    </div>
                    <div style={S.dwFieldWrap}>
                      <label style={S.fieldLabel}>Client name</label>
                      <input value={dwClientName} onChange={e => setDwClientName(e.target.value)} placeholder="Who is signing on behalf of the client?" style={S.fieldInput} />
                    </div>
                    <div style={S.dwYesNo}>
                      <button style={S.dwYesNoBtn(dwSignoffMode==='glass', true)} onClick={() => setDwSignoffMode('glass')}>Client Signs Here</button>
                      <button style={S.dwYesNoBtn(dwSignoffMode==='email', false)} onClick={() => setDwSignoffMode('email')}>Email Client</button>
                    </div>
                    {dwSignoffMode === 'glass' ? (
                      <div style={{display:'flex', flexDirection:'column', gap:8}}>
                        <div style={{fontSize:12.5, color:'var(--muted)'}}>Hand the device to the client to sign below</div>
                        <canvas
                          ref={dwSigCanvasRef} width={378} height={160}
                          onPointerDown={dwOnSigDown} onPointerMove={dwOnSigMove} onPointerUp={dwOnSigUp} onPointerLeave={dwOnSigUp}
                          style={{width:'100%', height:160, background:'var(--surface2)', border:'1px dashed var(--border)', borderRadius:8, touchAction:'none'}}
                        />
                        <button onClick={dwClearSignature} style={{alignSelf:'flex-start', border:'none', background:'none', color:'var(--accent)', fontFamily:'var(--font-head)', fontSize:12, fontWeight:700, letterSpacing:.5, textTransform:'uppercase', cursor:'pointer', padding:'4px 0'}}>Clear</button>
                      </div>
                    ) : (
                      <div style={S.dwFieldWrap}>
                        <label style={S.fieldLabel}>Client email</label>
                        <input value={dwClientEmail} onChange={e => setDwClientEmail(e.target.value)} placeholder="client@company.co.nz" style={S.fieldInput} />
                        <div style={{fontSize:12, color:'var(--muted)'}}>The client will get a link to review and sign the PDF sheet remotely.</div>
                      </div>
                    )}
                  </div>
                )}

                <div style={{padding:'20px 16px 4px', display:'flex', gap:10}}>
                  {dwIdx > 0 && (
                    <button onClick={dwGoPrevTab} style={{flex:'none', border:'1px solid var(--border)', background:'transparent', color:'var(--muted)', borderRadius:6, padding:'14px 18px', fontFamily:'var(--font-head)', fontSize:14, fontWeight:700, letterSpacing:.5, textTransform:'uppercase', cursor:'pointer'}}>Back</button>
                  )}
                  <button
                    onClick={() => dwIsLastTab ? dwSubmitForm() : dwGoNext()}
                    disabled={dwSubmitting}
                    style={{flex:1, border:'none', background:'var(--accent)', color:'#fff', borderRadius:6, padding:14, fontFamily:'var(--font-head)', fontSize:15, fontWeight:700, letterSpacing:1, textTransform:'uppercase', cursor:'pointer', opacity: dwSubmitting ? .6 : 1}}
                  >
                    {dwIsLastTab ? (dwSubmitting ? 'Saving…' : (dwSignoffMode === 'email' ? 'Send for signature' : 'Complete')) : 'Next'}
                  </button>
                </div>
                {dwValidationMsg && <div style={{padding:'8px 16px 24px', fontSize:12.5, color:'var(--danger)', textAlign:'center'}}>{dwValidationMsg}</div>}
              </div>
            )}

            {dwView === 'new' && dwStep === 'complete' && dwLastSubmitted && (
              <div style={{...S.logCard, ...S.dwCompleteWrap}}>
                <div style={S.dwCheckCircle}>✓</div>
                <div style={{fontFamily:'var(--font-head)', fontSize:22, fontWeight:800, letterSpacing:.5, textTransform:'uppercase', color:'var(--text)'}}>Dayworks sheet sent</div>
                <div style={{fontSize:14, color:'var(--muted)', lineHeight:1.5}}>
                  A PDF summary with all labour, materials, photos and the client's sign-off{' '}
                  {dwLastSubmitted.signoff_mode === 'email'
                    ? <>has been emailed to <b style={{color:'var(--text)'}}>{dwLastSubmitted.client_email}</b> for the client to sign</>
                    : <>has been filed against {dwLastSubmitted.job}</>}.
                </div>
                {dwWebhookUrl ? (
                  <div style={S.dwWebhookNote}><span style={{fontSize:15}}>📧</span><span>Sent to your configured automation for emailing</span></div>
                ) : (
                  <div style={S.dwWebhookNote}><span style={{fontSize:15}}>ℹ️</span><span>No automation webhook configured yet — add one in Settings to auto-email this via Make.com</span></div>
                )}
                <button onClick={() => setDwStep('pdfPreview')} style={{border:'1px solid var(--border)', background:'transparent', color:'var(--muted)', borderRadius:6, padding:'10px 18px', fontFamily:'var(--font-head)', fontSize:12.5, fontWeight:700, letterSpacing:.5, textTransform:'uppercase', cursor:'pointer'}}>Preview PDF sent</button>
                <button onClick={() => { setDwView('log'); dwResetForm() }} style={{marginTop:8, border:'none', background:'var(--accent)', color:'#fff', borderRadius:6, padding:'12px 22px', fontFamily:'var(--font-head)', fontSize:14, fontWeight:700, letterSpacing:1, textTransform:'uppercase', cursor:'pointer'}}>View Log</button>
                <button onClick={dwStartNew} style={{border:'none', background:'none', color:'var(--muted)', fontFamily:'var(--font-head)', fontSize:12, fontWeight:700, letterSpacing:1, textTransform:'uppercase', cursor:'pointer', padding:6}}>Start another sheet</button>
              </div>
            )}

            {dwView === 'new' && dwStep === 'pdfPreview' && dwLastSubmitted && (() => {
              const ent = dwLastSubmitted
              const loc = ent.location || ''
              const pdfLocationPart = loc.split('/')[0] || '—'
              const pdfGridPart = (loc.match(/grid\s*(.+)$/i) || [])[1] || (loc.split('·')[1] || '—')
              const labourRows = ent.labour_rows || []
              const materialRows = ent.material_rows || []
              const photos = ent.photos || []
              return (
                <div style={S.dwPdfPage}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14}}>
                    <button onClick={() => setDwStep('complete')} style={{border:'none', background:'none', fontSize:14, color:'#3f5064', cursor:'pointer', fontFamily:'var(--font-head)', fontWeight:700, letterSpacing:.5, textTransform:'uppercase'}}>← Back</button>
                    <div style={{fontSize:11, color:'#6a8099'}}>{dwWebhookUrl ? 'Sent to your configured automation' : 'No automation configured'}</div>
                  </div>
                  <div style={S.dwPdfSheet}>
                    <div style={{fontSize:17, fontWeight:700, borderBottom:'2px solid #1a1f27', paddingBottom:8, marginBottom:12}}>Daily Labour Records</div>
                    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'6px 14px', fontSize:11.5, marginBottom:14}}>
                      <div><b>Job Number / Name:</b> {ent.job}</div>
                      <div><b>Date:</b> {String(ent.entry_date).slice(0,10)}</div>
                      <div><b>Location:</b> {pdfLocationPart}</div>
                      <div><b>Grid:</b> {pdfGridPart}</div>
                      {ent.variation === 'Yes' && <div><b>Variation No:</b> {ent.vo_number}</div>}
                    </div>
                    <table style={{width:'100%', borderCollapse:'collapse', fontSize:10.5, marginBottom:14}}>
                      <thead><tr>
                        {['Name','Activity','Start','Finish','Total hours','Chargeable hours'].map(h => <th key={h} style={S.dwPdfTh}>{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {labourRows.map((row,i) => (
                          <tr key={i}>
                            <td style={S.dwPdfTd}>{row.name}</td>
                            <td style={S.dwPdfTd}>{row.activity}</td>
                            <td style={S.dwPdfTd}>{row.start}</td>
                            <td style={S.dwPdfTd}>{row.end}</td>
                            <td style={S.dwPdfTd}>{row.hoursLabel}</td>
                            <td style={S.dwPdfTd}>{row.hoursLabel}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div style={{fontSize:12, fontWeight:700, marginBottom:6}}>Materials</div>
                    <table style={{width:'100%', borderCollapse:'collapse', fontSize:10.5, marginBottom:14}}>
                      <thead><tr>{['Item','Qty','Unit'].map(h => <th key={h} style={S.dwPdfTh}>{h}</th>)}</tr></thead>
                      <tbody>
                        {materialRows.map((row,i) => (
                          <tr key={i}><td style={S.dwPdfTd}>{row.item}</td><td style={S.dwPdfTd}>{row.qty}</td><td style={S.dwPdfTd}>{row.unit}</td></tr>
                        ))}
                      </tbody>
                    </table>
                    {photos.length > 0 && (
                      <>
                        <div style={{fontSize:12, fontWeight:700, marginBottom:6}}>Photos ({photos.length})</div>
                        <div style={{display:'flex', flexWrap:'wrap', gap:6, marginBottom:14}}>
                          {photos.map((p,i) => <img key={i} src={p.src} style={{width:52, height:52, objectFit:'cover', border:'1px solid #ccc', borderRadius:3}} />)}
                        </div>
                      </>
                    )}
                    <div style={{fontSize:12, fontWeight:700, borderTop:'1px solid #ccc', paddingTop:10, marginTop:4}}>Client sign off</div>
                    <div style={{fontSize:11, marginTop:8}}>Signature:</div>
                    <div style={{border:'1px dashed #ccc', borderRadius:4, height:56, display:'flex', alignItems:'center', justifyContent:'center', marginTop:4}}>
                      {ent.signature_data_url ? <img src={ent.signature_data_url} style={{maxHeight:52}} /> : <span style={{fontSize:10.5, color:'#9aa3b0'}}>Signed remotely by client</span>}
                    </div>
                    <div style={{fontSize:11, marginTop:8}}>Name: {ent.client_name || '—'} &nbsp;&nbsp; Date: {String(ent.entry_date).slice(0,10)}</div>
                  </div>
                </div>
              )
            })()}

            {dwView === 'log' && (
              <div style={S.logCard}>
                <div style={S.logHeader}>
                  <div style={S.logTitleRow}>
                    <div style={S.logTitle}>Dayworks Log ({dwFilteredLog.length})</div>
                    <button style={S.exportBtn} onClick={dwStartNew}>+ New</button>
                  </div>
                  <div style={{display:'flex', flexDirection:'column', gap:8}}>
                    <input value={dwFilterJob} onChange={e => setDwFilterJob(e.target.value)} placeholder="Search by job name" style={S.fieldInput} />
                    <div style={{display:'flex', gap:8}}>
                      <select value={dwFilterVariation} onChange={e => setDwFilterVariation(e.target.value)} style={{...S.fieldSelect, flex:1}}>
                        <option value="all">All work types</option>
                        <option value="Yes">Variation (VO) only</option>
                        <option value="No">Non-variation only</option>
                      </select>
                      <select value={dwFilterStatus} onChange={e => setDwFilterStatus(e.target.value)} style={{...S.fieldSelect, flex:1}}>
                        <option value="all">All statuses</option>
                        <option value="Signed on glass">Signed on-site</option>
                        <option value="Sent to client">Awaiting client</option>
                      </select>
                    </div>
                  </div>
                </div>
                {dwFilteredLog.length === 0 ? (
                  <div style={S.empty}>No dayworks sheets match yet</div>
                ) : (
                  <div style={{padding:'14px 16px', display:'flex', flexDirection:'column', gap:10}}>
                    {dwFilteredLog.map(e => {
                      const labourHoursTotal = (e.labour_rows || []).reduce((sum, r) => { const n = parseFloat(r.hoursLabel); return sum + (isNaN(n) ? 0 : n) }, 0)
                      const statusColor = e.status === 'Signed on glass' ? '#4caf7d' : '#E8A33D'
                      return (
                        <div key={e.id} style={S.dwLogCard}>
                          <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:8}}>
                            <div>
                              <div style={{fontFamily:'var(--font-head)', fontSize:16, fontWeight:700, letterSpacing:.3, color:'var(--text)'}}>{e.job}</div>
                              <div style={{fontSize:12, color:'var(--muted)', marginTop:2}}>
                                {String(e.entry_date).slice(0,10)}
                                {e.variation === 'Yes' && <> · <span style={{color:'var(--accent)', fontWeight:700}}>{e.vo_number}</span></>}
                              </div>
                            </div>
                            <div style={S.dwStatusBadge(statusColor)}>{e.status}</div>
                          </div>
                          <div style={{display:'flex', gap:16, marginTop:10, fontSize:12.5, color:'#9db0c2'}}>
                            <div>{labourHoursTotal ? labourHoursTotal.toFixed(1).replace(/\.0$/,'') : 0} labour hrs</div>
                            <div>{(e.material_rows||[]).length} materials</div>
                            <div>{(e.photos||[]).length} photos</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
          )
        })()}

        {/* ── REFERENCE TAB ────────────────────────────────────────── */}
        {tab === 'reference' && (
          <div style={S.logCard}>
            <div style={S.logHeader}>
              <div style={{display:'flex', gap:0, marginBottom:14, borderRadius:6, overflow:'hidden', border:'1px solid var(--border)', width:'fit-content'}}>
                {[['tools',`🔧 Tools (${handTools.length})`],['products',`📦 Products (${products.length})`]].map(([t,label]) => (
                  <button key={t} onClick={() => { setRefTab(t); setRefSearch('') }} style={{
                    padding:'7px 20px', background: refTab===t ? 'var(--accent)' : 'transparent',
                    color: refTab===t ? '#fff' : 'var(--muted)', border:'none',
                    fontFamily:'var(--font-head)', fontWeight:700, fontSize:13, letterSpacing:1,
                    textTransform:'uppercase', cursor:'pointer', transition:'all .15s',
                  }}>{label}</button>
                ))}
              </div>
              <input
                style={S.fieldInput}
                placeholder={refTab === 'tools' ? 'Search tools…' : 'Search products by name, code, or supplier…'}
                value={refSearch}
                onChange={e => setRefSearch(e.target.value)}
                autoFocus
              />
            </div>

            {refTab === 'tools' ? (() => {
              const q = refSearch.trim().toLowerCase()
              const filtered = handTools.filter(t => t.name.toLowerCase().includes(q))
              return filtered.length === 0 ? (
                <div style={S.empty}>No tools match</div>
              ) : (
                <>
                  <div style={{display:'grid', gridTemplateColumns:'1fr 90px', gap:8, padding:'10px 20px', borderBottom:'2px solid var(--border)'}}>
                    <div style={S.logHead}>Tool</div>
                    <div style={S.logHead}>Cost</div>
                  </div>
                  {filtered.map((t,i) => (
                    <div key={i} style={{display:'grid', gridTemplateColumns:'1fr 90px', gap:8, padding:'11px 20px', borderBottom:'1px solid var(--border)', alignItems:'center', fontSize:13}}>
                      <div style={{display:'flex', alignItems:'center', gap:6, color:'var(--text)'}}><span>🔧</span>{t.name}</div>
                      <div style={{color:'var(--muted)'}}>{t.cost != null ? `$${t.cost}` : '—'}</div>
                    </div>
                  ))}
                </>
              )
            })() : (() => {
              const q = refSearch.trim().toLowerCase()
              const filtered = !q ? products.slice(0, 50) : products.filter(p =>
                p.description?.toLowerCase().includes(q) ||
                p.code?.toLowerCase().includes(q) ||
                p.alias?.toLowerCase().includes(q) ||
                p.supplier?.toLowerCase().includes(q)
              )
              return (
                <>
                  {!q && (
                    <div style={{padding:'10px 20px 0', fontSize:12, color:'var(--muted)'}}>Showing first 50 of {products.length} — search to narrow</div>
                  )}
                  {filtered.length === 0 ? <div style={S.empty}>No products match</div> : (
                    <>
                      <div style={{display:'grid', gridTemplateColumns:'110px 1fr 100px', gap:8, padding:'10px 20px', borderBottom:'2px solid var(--border)'}}>
                        <div style={S.logHead}>Code</div>
                        <div style={S.logHead}>Description</div>
                        <div style={S.logHead}>Supplier</div>
                      </div>
                      {filtered.map(p => (
                        <div key={p.code} style={{display:'grid', gridTemplateColumns:'110px 1fr 100px', gap:8, padding:'11px 20px', borderBottom:'1px solid var(--border)', alignItems:'center', fontSize:13}}>
                          <div style={{fontFamily:'var(--font-head)', fontWeight:700, color:'var(--accent)', fontSize:12}}>{p.code}</div>
                          <div style={{color:'var(--text)'}}>{p.description}</div>
                          <div style={{color:'var(--muted)', fontSize:12}}>{p.supplier}</div>
                        </div>
                      ))}
                    </>
                  )}
                </>
              )
            })()}
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

            {/* Lock config */}
            <div style={S.settingSection}>
              <div style={S.settingTitle}>Room Lock</div>
              <div style={S.settingDesc}>Let a keyholder lock the room before heading out. While locked, every stock entry fires an alert to a webhook (Make, Zapier, etc.) so they know what was taken.</div>
              <div style={S.field}><label style={S.fieldLabel}>Unlock PIN</label><input style={{...S.syncInput,maxWidth:160}} value={lockPin} onChange={e => { setLockPin(e.target.value); localStorage.setItem('sb_pin', e.target.value) }} placeholder="e.g. 4729" maxLength={6} /></div>
              <div style={S.field}><label style={S.fieldLabel}>Alert recipient (shown in banner &amp; notifications)</label><input style={S.syncInput} value={lockNote} onChange={e => { setLockNote(e.target.value); localStorage.setItem('sb_lock_note', e.target.value) }} placeholder="e.g. Hemi Walker" /></div>
              <div style={S.field}><label style={S.fieldLabel}>Webhook URL (Make / Zapier)</label><input style={S.syncInput} value={lockWebhook} onChange={e => { setLockWebhook(e.target.value); localStorage.setItem('sb_lock_webhook', e.target.value) }} placeholder="https://hook.make.com/..." /></div>
              <div style={S.field}><label style={S.fieldLabel}>Test</label>
                <button style={S.syncBtn} onClick={() => setShowLockModal(true)}>Try locking the room</button>
              </div>
            </div>

            {/* Day Works automation */}
            <div style={S.settingSection}>
              <div style={S.settingTitle}>Day Works Automation</div>
              <div style={S.settingDesc}>When a Day Works sheet is submitted, the app POSTs the full sheet (job, labour, materials, photos, signature, sign-off details) to this webhook. Point it at a Make.com scenario to handle emailing the client and accountspayable@sansom.co.nz.</div>
              <div style={S.field}>
                <label style={S.fieldLabel}>Make.com Webhook URL</label>
                <input style={S.syncInput} value={dwWebhookUrl} onChange={e => { setDwWebhookUrl(e.target.value); localStorage.setItem('sb_dayworks_webhook', e.target.value) }} placeholder="https://hook.make.com/..." />
              </div>
            </div>

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

            {/* Entry source tracker (voice vs type) */}
            <div style={S.settingSection}>
              <div style={S.settingTitle}>Entry Source</div>
              <div style={S.settingDesc}>How workers are logging entries — by speaking into the mic or typing manually.</div>
              {(() => {
                const all = [...entries, ...toolEntries]
                const voiceCount = all.filter(e => e.source === 'voice').length
                const textCount = all.filter(e => e.source === 'text').length
                const unknownCount = all.length - voiceCount - textCount
                const total = all.length || 1
                const pct = n => Math.round((n / total) * 100)
                return (
                  <>
                    <div style={{display:'flex', gap:16, flexWrap:'wrap', marginBottom:14}}>
                      <div style={{background:'var(--surface2)', borderRadius:8, padding:'12px 18px', border:'1px solid var(--border)', flex:1, minWidth:140}}>
                        <div style={{fontSize:11, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:4}}>🎤 VOICE</div>
                        <div style={{fontFamily:'var(--font-head)', fontSize:24, fontWeight:800, color:'var(--accent)'}}>{voiceCount}</div>
                        <div style={{fontSize:11, color:'var(--muted)'}}>{pct(voiceCount)}% of entries</div>
                      </div>
                      <div style={{background:'var(--surface2)', borderRadius:8, padding:'12px 18px', border:'1px solid var(--border)', flex:1, minWidth:140}}>
                        <div style={{fontSize:11, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:4}}>⌨️ TYPED</div>
                        <div style={{fontFamily:'var(--font-head)', fontSize:24, fontWeight:800, color:'var(--accent)'}}>{textCount}</div>
                        <div style={{fontSize:11, color:'var(--muted)'}}>{pct(textCount)}% of entries</div>
                      </div>
                      {unknownCount > 0 && (
                        <div style={{background:'var(--surface2)', borderRadius:8, padding:'12px 18px', border:'1px solid var(--border)', flex:1, minWidth:140}}>
                          <div style={{fontSize:11, color:'var(--muted)', fontFamily:'var(--font-head)', letterSpacing:1, marginBottom:4}}>UNKNOWN</div>
                          <div style={{fontFamily:'var(--font-head)', fontSize:24, fontWeight:800, color:'var(--muted)'}}>{unknownCount}</div>
                          <div style={{fontSize:11, color:'var(--muted)'}}>logged before tracking</div>
                        </div>
                      )}
                    </div>
                    <div style={{height:8, borderRadius:4, overflow:'hidden', display:'flex', background:'var(--surface2)', border:'1px solid var(--border)'}}>
                      <div style={{width:`${pct(voiceCount)}%`, background:'var(--accent)'}} />
                      <div style={{width:`${pct(textCount)}%`, background:'#E8A33D'}} />
                    </div>
                  </>
                )
              })()}
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
