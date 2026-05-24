export type PreviewAutoplayMode = 'viewport' | 'hover' | 'off';

export type PreviewPreferences = {
  autoplayMode: PreviewAutoplayMode;
  /** Cycle JPEG frames when no preview clip exists */
  flipbookFallback: boolean;
};

export const DEFAULT_PREVIEW_PREFERENCES: PreviewPreferences = {
  autoplayMode: 'viewport',
  flipbookFallback: true,
};

const STORAGE_KEY = 'cinetag.preview.preferences';

export function loadPreviewPreferences(): PreviewPreferences {
  if (typeof window === 'undefined') return DEFAULT_PREVIEW_PREFERENCES;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREVIEW_PREFERENCES;
    const parsed = JSON.parse(raw) as Partial<PreviewPreferences>;
    return {
      autoplayMode:
        parsed.autoplayMode === 'hover' ||
        parsed.autoplayMode === 'off' ||
        parsed.autoplayMode === 'viewport'
          ? parsed.autoplayMode
          : DEFAULT_PREVIEW_PREFERENCES.autoplayMode,
      flipbookFallback:
        typeof parsed.flipbookFallback === 'boolean'
          ? parsed.flipbookFallback
          : DEFAULT_PREVIEW_PREFERENCES.flipbookFallback,
    };
  } catch {
    return DEFAULT_PREVIEW_PREFERENCES;
  }
}

export function savePreviewPreferences(prefs: PreviewPreferences) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}
