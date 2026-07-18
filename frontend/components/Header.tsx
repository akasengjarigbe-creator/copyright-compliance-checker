export default function Header() {
  return (
    <header className="mb-8 text-center">
      <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
        AI-assisted assessment
      </p>

      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
        Copyright Compliance Checker
      </h1>

      <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-600">
        Analyse webpages, HTML source code, or ZIP website submissions using
        rule-based checks, AI reasoning, and a transparent comparison of both
        results.
      </p>
    </header>
  );
}