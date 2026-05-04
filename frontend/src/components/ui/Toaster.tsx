import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { dismissToast, useToasts, type Toast, type ToastTone } from '@/components/ui/toastStore';

const toneClasses: Record<ToastTone, string> = {
  info: 'border-blue-500/40 bg-bg-1',
  success: 'border-success/50 bg-bg-1',
  warning: 'border-warning/50 bg-bg-1',
  danger: 'border-accent/60 bg-bg-1',
};

const toneIcon: Record<ToastTone, JSX.Element> = {
  info: <Info className="h-5 w-5 text-blue-300" aria-hidden />,
  success: <CheckCircle2 className="h-5 w-5 text-success" aria-hidden />,
  warning: <AlertTriangle className="h-5 w-5 text-warning" aria-hidden />,
  danger: <AlertTriangle className="h-5 w-5 text-accent" aria-hidden />,
};

export function Toaster(): JSX.Element {
  const items = useToasts();
  return (
    <div
      role="region"
      aria-label="Notifications"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 px-4 pb-6 sm:items-end sm:pb-8 sm:pr-8"
    >
      <AnimatePresence initial={false}>
        {items.map((t) => (
          <ToastView key={t.id} toast={t} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastView({ toast: t }: { toast: Toast }): JSX.Element {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.96 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      role={t.tone === 'danger' || t.tone === 'warning' ? 'alert' : 'status'}
      className={cn(
        'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-lg border px-4 py-3 shadow-card backdrop-blur',
        toneClasses[t.tone],
      )}
    >
      <span className="mt-0.5">{toneIcon[t.tone]}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-text-0">{t.title}</p>
        {t.description ? (
          <p className="mt-0.5 line-clamp-3 text-xs text-text-1">{t.description}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={() => dismissToast(t.id)}
        aria-label="Dismiss notification"
        className="-mr-1 rounded p-1 text-text-2 transition-colors hover:bg-bg-2 hover:text-text-0"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </motion.div>
  );
}
