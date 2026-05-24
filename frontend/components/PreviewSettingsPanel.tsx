'use client';

import { usePreviewPreferences } from '@/components/providers/PreviewPreferencesProvider';
import type { PreviewAutoplayMode } from '@/lib/preview-preferences';
import { Button } from '@/components/ui/button';

export default function PreviewSettingsPanel() {
  const { autoplayMode, flipbookFallback, setAutoplayMode, setFlipbookFallback } =
    usePreviewPreferences();

  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px] text-white/60">
      <span className="text-white/45">Previews</span>
      {(['viewport', 'hover', 'off'] as PreviewAutoplayMode[]).map((mode) => (
        <Button
          key={mode}
          type="button"
          size="sm"
          variant={autoplayMode === mode ? 'default' : 'secondary'}
          className="!h-7 !px-2.5 !text-[10px] capitalize"
          onClick={() => setAutoplayMode(mode)}
        >
          {mode}
        </Button>
      ))}
      <label className="inline-flex items-center gap-1.5 ml-1 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={flipbookFallback}
          onChange={(e) => setFlipbookFallback(e.target.checked)}
          className="accent-cinetag-red"
        />
        flipbook fallback
      </label>
    </div>
  );
}
