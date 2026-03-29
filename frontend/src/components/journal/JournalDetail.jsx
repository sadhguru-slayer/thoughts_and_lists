import { formatJournalDetailDate } from "@/lib/formatDate";

function FieldReadonly({ field }) {
  const isCheckbox = field.field_type === "checkbox";
  const checked =
    field.value === "true" ||
    field.value === true ||
    String(field.value).toLowerCase() === "true";

  if (isCheckbox) {
    return (
      <div className="flex items-center justify-between gap-3 py-2">
        <span className="text-sm text-zinc-600 dark:text-zinc-400">
          {field.label}
        </span>
        <span
          className={`inline-flex h-6 w-11 shrink-0 rounded-full p-0.5 transition-colors ${
            checked ? "bg-emerald-500/90" : "bg-zinc-200 dark:bg-zinc-600"
          }`}
        >
          <span
            className={`block h-5 w-5 rounded-full bg-white shadow transition-transform ${
              checked ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </span>
      </div>
    );
  }

  if (field.field_type === "textarea") {
    return (
      <div className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {field.label}
        </p>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-900 dark:text-zinc-100">
          {field.value ?? "—"}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {field.label}
      </p>
      <p className="text-sm text-zinc-900 dark:text-zinc-100">
        {field.value ?? "—"}
      </p>
    </div>
  );
}

export default function JournalDetail({ detail, onBack, onDelete }) {
  const handleDelete = () => {
    if (
      typeof window !== "undefined" &&
      window.confirm("Delete this journal entry? This cannot be undone.")
    ) {
      onDelete(detail.id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800 dark:focus-visible:ring-zinc-500 dark:focus-visible:ring-offset-zinc-950"
        >
          <span aria-hidden>←</span>
          Back
        </button>
        <button
          type="button"
          onClick={handleDelete}
          className="ml-auto inline-flex items-center rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-800 transition hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200 dark:hover:bg-red-950/70 dark:focus-visible:ring-red-500 dark:focus-visible:ring-offset-zinc-950"
        >
          Delete
        </button>
      </div>

      <header className="space-y-2">
        <time
          dateTime={detail.date}
          className="text-sm font-medium text-zinc-500 dark:text-zinc-400"
        >
          {formatJournalDetailDate(detail.date)}
        </time>
        <h2 className="text-lg font-semibold leading-snug text-zinc-900 dark:text-zinc-50">
          Journal entry
        </h2>
      </header>

      <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Content
        </h3>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-zinc-900 dark:text-zinc-100">
          {detail.content ?? "—"}
        </p>
      </section>

      {detail.sections?.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Sections
          </h3>
          {detail.sections.map((section) => (
            <article
              key={section.id}
              className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              <h4 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
                {section.name}
              </h4>
              <div className="mt-4 flex flex-col gap-4 divide-y divide-zinc-100 dark:divide-zinc-800">
                {section.field_values?.map((fv) => (
                  <div key={fv.id} className="pt-4 first:pt-0">
                    <FieldReadonly field={fv} />
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
