import { useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'

export default function ConfirmModal({ title, body, confirmWord = 'AKTIFKAN', confirmLabel, onConfirm, onCancel }) {
  const [typed, setTyped] = useState('')
  const ready = typed.trim().toUpperCase() === confirmWord

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="panel border-short/50 max-w-md w-full p-6">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2 text-short">
            <AlertTriangle size={20} />
            <h3 className="font-display font-semibold text-base">{title}</h3>
          </div>
          <button onClick={onCancel} className="text-ink-faint hover:text-ink"><X size={18} /></button>
        </div>
        <p className="text-sm text-ink-muted leading-relaxed mb-4">{body}</p>
        <label className="text-xs text-ink-muted font-mono">
          Ketik <span className="text-short font-semibold">{confirmWord}</span> buat konfirmasi
        </label>
        <input
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          className="w-full mt-1.5 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring"
          autoFocus
        />
        <div className="flex gap-2 mt-4">
          <button onClick={onCancel} className="flex-1 py-2.5 rounded-md text-sm font-medium border border-line text-ink-muted hover:bg-raised transition">
            Batal
          </button>
          <button
            onClick={onConfirm}
            disabled={!ready}
            className="flex-1 py-2.5 rounded-md text-sm font-semibold bg-short text-void disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 transition"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
