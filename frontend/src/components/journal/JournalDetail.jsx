"use client";

import { formatJournalDetailDate } from "@/lib/formatDate";
import { motion } from "framer-motion";
import { ArrowLeft, Trash2 } from "lucide-react";

function FieldReadonly({ field }) {
  const isCheckbox = field.field_type === "checkbox";
  const checked =
    field.value === "true" ||
    field.value === true ||
    String(field.value).toLowerCase() === "true";

  if (isCheckbox) {
    return (
      <div className="flex items-center justify-between gap-3 py-3">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {field.label}
        </span>
        <span
          className={`inline-flex h-6 w-11 shrink-0 rounded-full p-0.5 transition-colors duration-300 ${checked ? "bg-zinc-900 dark:bg-zinc-100" : "bg-zinc-200 dark:bg-zinc-700"
            }`}
        >
          <span
            className={`block h-5 w-5 rounded-full bg-white dark:bg-zinc-900 shadow transition-transform duration-300 ${checked ? "translate-x-5" : "translate-x-0"
              }`}
          />
        </span>
      </div>
    );
  }

  if (field.field_type === "textarea") {
    return (
      <div className="space-y-2 py-2">
        <p className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          {field.label}
        </p>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-800 dark:text-zinc-200 bg-zinc-50/50 dark:bg-zinc-900/50 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800">
          {field.value ?? "—"}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1 py-1">
      <p className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
        {field.label}
      </p>
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
        {field.value ?? "—"}
      </p>
    </div>
  );
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

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
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants} className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800 active:scale-95"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          type="button"
          onClick={handleDelete}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-100 hover:text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/60 active:scale-95"
        >
          <Trash2 className="w-4 h-4" />
          Delete
        </button>
      </motion.div>

      <motion.header variants={itemVariants} className="space-y-2 py-2">
        <time
          dateTime={detail.date}
          className="text-sm font-bold tracking-widest uppercase text-zinc-500 dark:text-zinc-400"
        >
          {formatJournalDetailDate(detail.date)}
        </time>
        <h2 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Journal Entry
        </h2>
      </motion.header>

      {detail.content && (
        <motion.section variants={itemVariants} className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 mb-4">
            Content
          </h3>
          <p className="whitespace-pre-wrap text-base leading-relaxed text-zinc-800 dark:text-zinc-200 font-medium">
            {detail.content}
          </p>
        </motion.section>
      )}

      {detail.sections?.length > 0 && (
        <motion.div variants={itemVariants} className="space-y-4 pt-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 mb-2">
            Sections
          </h3>
          <div className="grid gap-4">
            {detail.sections.map((section) => (
              <article
                key={section.id}
                className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
              >
                <h4 className="text-lg font-bold text-zinc-900 dark:text-zinc-50 pb-2 border-b border-zinc-100 dark:border-zinc-800/50 mb-2">
                  {section.name}
                </h4>
                <div className="flex flex-col gap-2 divide-y divide-zinc-100 dark:divide-zinc-800/50">
                  {section.field_values?.map((fv) => (
                    <FieldReadonly key={fv.id} field={fv} />
                  ))}
                </div>
              </article>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
