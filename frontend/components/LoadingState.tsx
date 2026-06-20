type LoadingStateProps = {
  isVisible: boolean;
};

export function LoadingState({ isVisible }: LoadingStateProps) {
  if (!isVisible) {
    return null;
  }

  return (
    <section className="rounded-lg border border-line bg-white/80 p-4 text-sm text-muted" role="status">
      Checking service health through the local gateway...
    </section>
  );
}
