import { useStore } from "../store";

export function ErrorBanner() {
  const triggerError = useStore((s) => s.triggerError);
  const dismissError = useStore((s) => s.dismissError);

  if (!triggerError) return null;

  return (
    <div
      role="alert"
      className="mb-4 flex items-center justify-between gap-4 rounded-lg border border-red-500/40 bg-red-950/60 px-4 py-3 text-sm text-red-200"
    >
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className="font-bold text-red-400">
          !
        </span>
        <span>{triggerError}</span>
      </div>
      <button
        type="button"
        onClick={dismissError}
        aria-label="Dismiss error"
        className="rounded px-2 py-1 text-xs font-medium text-red-300 hover:bg-red-900/60 hover:text-white"
      >
        Dismiss
      </button>
    </div>
  );
}
