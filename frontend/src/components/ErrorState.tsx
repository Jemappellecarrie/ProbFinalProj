interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <section className="panel status-panel error-panel">
      <p className="eyebrow">Request Failed</p>
      <h2>Something blocked the demo flow.</h2>
      <p>{message}</p>
      <button className="secondary-button" onClick={onRetry}>
        Retry
      </button>
    </section>
  );
}
