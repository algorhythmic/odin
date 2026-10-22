export function NotFound({ title, message, href, linkText }) {
  return (
    <section class="not-found" role="alert" data-testid="not-found">
      <h2>{title}</h2>
      <p>{message}</p>
      <a href={href}>{linkText}</a>
    </section>
  );
}
