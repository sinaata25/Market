// رندر اسکیمای JSON-LD در صفحه (سمت سرور)
export default function JsonLd({ data }: { data: unknown }) {
  if (!data) return null;
  // Escaping "<" prevents a value containing </script> from breaking out of
  // the JSON-LD script element. The JSON remains semantically identical.
  const json = JSON.stringify(data).replace(/</g, "\\u003c");
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: json }}
    />
  );
}
