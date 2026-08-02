import { useEffect, useState, useCallback } from 'react'
import { Loader2, ShieldAlert, Zap } from 'lucide-react'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'
import LinkAccountForm from '../components/LinkAccountForm.jsx'

const PRESET_META = {
  conservative: { label: 'Conservative', desc: 'Risiko kecil, buat modal yang mau dijaga.' },
  balanced: { label: 'Balanced', desc: 'Default seimbang antara growth & safety.' },
  aggressive: { label: 'Aggressive', desc: 'Lot lebih besar, cocok kalau confident sama sinyalnya.' },
  full_send: { label: 'Full Send', desc: 'Margin ceiling tinggi banget — risiko wipeout nyata.' },
}

export default function RiskSettings() {
  const { selected, accounts } = useAccounts()
  const [cfg, setCfg] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = useCallback(async () => {
    if (!selected) return
    setCfg(await api.getRiskSettings(selected.id))
  }, [selected])

  useEffect(() => { load() }, [load])

  const applyPreset = async (preset) => {
    setSaving(true)
    setMsg(null)
    try {
      const updated = await api.updateRiskSettings(selected.id, { preset })
      setCfg(updated)
      setMsg({ type: 'ok', text: `Preset ${PRESET_META[preset].label} diterapkan.` })
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  const saveField = async (patch) => {
    setSaving(true)
    try {
      const updated = await api.updateRiskSettings(selected.id, { preset: 'custom', ...patch })
      setCfg(updated)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  if (accounts.length === 0) return <LinkAccountForm />
  if (!cfg) return <div className="text-sm text-ink-muted font-mono">Memuat…</div>

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold flex items-center gap-2">
          <ShieldAlert size={20} className="text-amber" /> Risk Settings
        </h1>
        <p className="text-sm text-ink-muted mt-1">{selected?.label} — semua parameter di sini kamu yang pegang kendali penuh.</p>
      </div>

      <div>
        <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Preset Agresivitas</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(PRESET_META).map(([key, meta]) => (
            <button key={key} onClick={() => applyPreset(key)} disabled={saving}
              className={`text-left p-3.5 rounded-lg border transition ${
                cfg.preset === key ? 'border-amber bg-amber-soft' : 'border-line bg-raised hover:border-ink-faint'
              }`}>
              <div className={`text-sm font-semibold ${cfg.preset === key ? 'text-amber' : 'text-ink'}`}>{meta.label}</div>
              <div className="text-[11px] text-ink-faint mt-1 leading-snug">{meta.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="panel p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold flex items-center gap-1.5">
              <Zap size={14} className="text-amber" /> Full Margin Mode
            </div>
            <p className="text-xs text-ink-muted mt-0.5 max-w-md leading-relaxed">
              Kalau nyala: pas swing/order block/S&R besar TERVALIDASI, sistem masang
              lot sampai batas ceiling margin di bawah — bukan risk % biasa. SL tetap tight,
              tapi satu order bisa makan margin gede. Risiko wipeout kalau breakout gagal.
            </p>
          </div>
          <button onClick={() => saveField({ full_margin_mode: !cfg.full_margin_mode })}
            className={`shrink-0 w-12 h-7 rounded-full transition relative ${cfg.full_margin_mode ? 'bg-short' : 'bg-line'}`}>
            <span className={`absolute top-1 w-5 h-5 rounded-full bg-ink transition-all ${cfg.full_margin_mode ? 'left-6' : 'left-1'}`} />
          </button>
        </div>

        <SliderRow label="Margin ceiling per order" value={cfg.max_margin_pct_per_trade} unit="%" min={1} max={95}
          onChange={(v) => saveField({ max_margin_pct_per_trade: v })} />
        <SliderRow label="Risk per trade (mode non-full-margin)" value={cfg.max_risk_pct_per_trade} unit="%" min={0.1} max={15} step={0.1}
          onChange={(v) => saveField({ max_risk_pct_per_trade: v })} />
        <SliderRow label="Ambang confidence AI buat entry" value={cfg.ai_confidence_threshold} unit="" min={0.5} max={0.95} step={0.01}
          onChange={(v) => saveField({ ai_confidence_threshold: v })} />
        <SliderRow label="Max posisi terbuka bersamaan" value={cfg.max_open_positions} unit="" min={1} max={15}
          onChange={(v) => saveField({ max_open_positions: v })} />
        <SliderRow label="Max trade per hari" value={cfg.max_daily_trades} unit="" min={1} max={60}
          onChange={(v) => saveField({ max_daily_trades: v })} />
      </div>

      <div className="panel p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">News Blackout Net</div>
            <p className="text-xs text-ink-muted mt-0.5 max-w-md leading-relaxed">
              Auto-pause order baru pas rilis berita high-impact (NFP, CPI, rate decision, dst).
              Ini rule keras, bukan opini AI.
            </p>
          </div>
          <button onClick={() => saveField({ news_blackout_enabled: !cfg.news_blackout_enabled })}
            className={`shrink-0 w-12 h-7 rounded-full transition relative ${cfg.news_blackout_enabled ? 'bg-long' : 'bg-line'}`}>
            <span className={`absolute top-1 w-5 h-5 rounded-full bg-ink transition-all ${cfg.news_blackout_enabled ? 'left-6' : 'left-1'}`} />
          </button>
        </div>
        <SliderRow label="Durasi blackout (sebelum & sesudah rilis)" value={cfg.news_blackout_minutes} unit=" menit" min={5} max={60}
          onChange={(v) => saveField({ news_blackout_minutes: v })} />
      </div>

      {msg && <p className={`text-xs ${msg.type === 'ok' ? 'text-long' : 'text-short'}`}>{msg.text}</p>}
      {saving && <p className="text-xs text-ink-faint flex items-center gap-1.5"><Loader2 size={12} className="animate-spin" /> Menyimpan…</p>}
    </div>
  )
}

function SliderRow({ label, value, unit, min, max, step = 1, onChange }) {
  const [local, setLocal] = useState(value)
  useEffect(() => setLocal(value), [value])

  return (
    <div>
      <div className="flex items-center justify-between text-xs font-mono mb-1.5">
        <span className="text-ink-muted">{label}</span>
        <span className="text-amber font-semibold">{local}{unit}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={local}
        onChange={(e) => setLocal(parseFloat(e.target.value))}
        onMouseUp={(e) => onChange(parseFloat(e.target.value))}
        onTouchEnd={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-amber-500"
      />
    </div>
  )
}
