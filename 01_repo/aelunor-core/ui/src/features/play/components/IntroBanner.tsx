interface IntroBannerProps {
  message: string | null;
}

export function IntroBanner({ message }: IntroBannerProps) {
  if (!message) {
    return null;
  }

  return (
    <section className="composer-intro-banner">
      <div className="session-feedback error">{message}</div>
    </section>
  );
}
