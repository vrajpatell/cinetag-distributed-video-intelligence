'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  DEFAULT_PREVIEW_PREFERENCES,
  loadPreviewPreferences,
  savePreviewPreferences,
  type PreviewAutoplayMode,
  type PreviewPreferences,
} from '@/lib/preview-preferences';

type PreviewPreferencesContextValue = PreviewPreferences & {
  setAutoplayMode: (mode: PreviewAutoplayMode) => void;
  setFlipbookFallback: (enabled: boolean) => void;
  reset: () => void;
};

const PreviewPreferencesContext = createContext<PreviewPreferencesContextValue | null>(null);

export function PreviewPreferencesProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<PreviewPreferences>(DEFAULT_PREVIEW_PREFERENCES);

  useEffect(() => {
    setPrefs(loadPreviewPreferences());
  }, []);

  const persist = useCallback((next: PreviewPreferences) => {
    setPrefs(next);
    savePreviewPreferences(next);
  }, []);

  const value = useMemo<PreviewPreferencesContextValue>(
    () => ({
      ...prefs,
      setAutoplayMode: (mode) => persist({ ...prefs, autoplayMode: mode }),
      setFlipbookFallback: (enabled) => persist({ ...prefs, flipbookFallback: enabled }),
      reset: () => persist(DEFAULT_PREVIEW_PREFERENCES),
    }),
    [persist, prefs],
  );

  return (
    <PreviewPreferencesContext.Provider value={value}>{children}</PreviewPreferencesContext.Provider>
  );
}

export function usePreviewPreferences() {
  const ctx = useContext(PreviewPreferencesContext);
  if (!ctx) {
    return {
      ...DEFAULT_PREVIEW_PREFERENCES,
      setAutoplayMode: () => undefined,
      setFlipbookFallback: () => undefined,
      reset: () => undefined,
    } satisfies PreviewPreferencesContextValue;
  }
  return ctx;
}
