import Header from "@/components/Header";
import UploadPanel from "@/components/UploadPanel";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <Header />

        <UploadPanel />

        <section className="mt-8 grid gap-4 sm:grid-cols-3">
          <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="font-semibold text-slate-900">
              Rule-Based Assessment
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-600">
              Applies deterministic copyright, attribution and
              licence compliance checks.
            </p>
          </article>

          <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="font-semibold text-slate-900">
              AI Assessment
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-600">
              Uses a local large language model to interpret
              attribution evidence and explain its reasoning.
            </p>
          </article>

          <article className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="font-semibold text-slate-900">
              Comparison
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-600">
              Compares the rule-based and AI assessments and
              highlights agreements, disagreements and cases
              requiring manual review.
            </p>
          </article>
        </section>
      </div>
    </main>
  );
}