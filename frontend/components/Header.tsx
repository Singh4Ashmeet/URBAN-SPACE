export function Header() {
  return (
    <header className="flex flex-col gap-3 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-3xl font-bold tracking-normal text-ink sm:text-4xl">UrbanShield</h1>
        <p className="mt-2 max-w-3xl text-base leading-7 text-muted">
          Phase 2 smart city monitoring, incident management, deterministic simulation, and offline-ready operations.
        </p>
      </div>
      <div className="rounded-md border border-teal-100 bg-teal-50 px-3 py-2 text-sm font-medium text-teal-700">
        Local development
      </div>
    </header>
  );
}
