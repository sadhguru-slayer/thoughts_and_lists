"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Plus, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";

function newClientKey() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `k-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function toDatetimeLocalValue(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function sectionFromTemplate(template) {
  const fields = [...template.fields].sort((a, b) => a.order - b.order);
  return {
    clientKey: newClientKey(),
    templateId: template.id,
    name: template.name,
    reusable: true,
    fieldValues: fields.map((f) => ({
      templateFieldId: f.id,
      label: f.label,
      field_type: f.field_type,
      value: f.field_type === "checkbox" ? "false" : "",
    })),
  };
}

function sectionFromLatestStructureEntry(apiSection, templates) {
  const tid = apiSection.template_id != null ? Number(apiSection.template_id) : null;
  const template = tid != null ? templates.find((t) => t.id === tid) : null;
  const rawFields = apiSection.fields ?? [];
  const fieldValues = rawFields.map((f, idx) => {
    let templateFieldId;
    if (template?.fields) {
      const ordered = [...template.fields].sort((a, b) => a.order - b.order);
      const match = ordered.find(
        (x) => x.label === f.label && x.field_type === f.field_type
      ) ?? ordered[idx];
      templateFieldId = match?.id;
    }
    return {
      templateFieldId,
      label: f.label,
      field_type: f.field_type,
      value: f.field_type === "checkbox" ? "false" : "",
    };
  });
  return {
    clientKey: newClientKey(),
    templateId: tid,
    name: apiSection.name ?? "",
    reusable: true,
    fieldValues,
  };
}

function emptyCustomSection(reusable = true) {
  return {
    clientKey: newClientKey(),
    templateId: null,
    name: "",
    reusable,
    fieldValues: [],
  };
}

function initialDraftSectionsFromLatest(latestStructure, templates) {
  if (!latestStructure?.sections?.length) return [];
  return latestStructure.sections.map((sec) =>
    sectionFromLatestStructureEntry(sec, templates)
  );
}

const FIELD_TYPES = [
  { value: "text", label: "Short text" },
  { value: "textarea", label: "Long text" },
  { value: "checkbox", label: "Checkbox" },
];

const inputClass = "w-full rounded-xl border border-zinc-200 bg-white/50 backdrop-blur-sm px-4 py-3 text-sm font-medium text-zinc-900 shadow-sm focus-visible:border-zinc-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400/50 dark:border-zinc-800 dark:bg-zinc-950/50 dark:text-zinc-100 dark:focus-visible:ring-zinc-600 dark:focus-visible:border-zinc-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed";

const labelClass = "text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 block mb-2";

function CustomFieldRow({ fieldIndex, fv, onChange, onRemove, disabled }) {
  if (fv.field_type === "checkbox") {
    return (
      <div className="flex items-center justify-between gap-3 rounded-xl border border-zinc-100 bg-white/40 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900/40">
        <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          {fv.label}
        </span>
        <div className="flex flex-col items-end sm:flex-row gap-3 sm:items-center">
          <label className="flex items-center cursor-pointer gap-2 scale-110 opacity-90 transition-opacity hover:opacity-100">
            <input
              type="checkbox"
              disabled={disabled}
              checked={fv.value === "true" || fv.value === true}
              onChange={(e) =>
                onChange(fieldIndex, e.target.checked ? "true" : "false")
              }
              className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600 disabled:opacity-50"
            />
          </label>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onRemove(fieldIndex)}
            className="p-1.5 text-zinc-400 hover:text-red-500 dark:hover:text-red-400 transition-colors rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-start justify-between gap-2 px-1">
        <label className={`${labelClass} mb-1 normal-case tracking-normal`}>{fv.label}</label>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onRemove(fieldIndex)}
          className="p-1 text-zinc-400 hover:text-red-500 transition-colors rounded-md disabled:opacity-50"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      {fv.field_type === "textarea" ? (
        <textarea
          rows={3}
          disabled={disabled}
          value={fv.value ?? ""}
          onChange={(e) => onChange(fieldIndex, e.target.value)}
          className={inputClass}
        />
      ) : (
        <input
          type="text"
          disabled={disabled}
          value={fv.value ?? ""}
          onChange={(e) => onChange(fieldIndex, e.target.value)}
          className={inputClass}
        />
      )}
    </div>
  );
}

function TemplateFieldRow({ fv, fieldIndex, onChange, disabled }) {
  if (fv.field_type === "checkbox") {
    return (
      <div className="flex items-center justify-between gap-3 rounded-xl border border-zinc-100 bg-white/40 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900/40">
        <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          {fv.label}
        </span>
        <label className="flex items-center cursor-pointer gap-2 scale-110 opacity-90 transition-opacity hover:opacity-100">
          <input
            type="checkbox"
            disabled={disabled}
            checked={fv.value === "true" || fv.value === true}
            onChange={(e) =>
              onChange(fieldIndex, e.target.checked ? "true" : "false")
            }
            className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600 disabled:opacity-50"
          />
        </label>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <label className={`${labelClass} px-1 mb-1 normal-case tracking-normal`}>{fv.label}</label>
      {fv.field_type === "textarea" ? (
        <textarea
          rows={3}
          disabled={disabled}
          value={fv.value ?? ""}
          onChange={(e) => onChange(fieldIndex, e.target.value)}
          className={inputClass}
        />
      ) : (
        <input
          type="text"
          disabled={disabled}
          value={fv.value ?? ""}
          onChange={(e) => onChange(fieldIndex, e.target.value)}
          className={inputClass}
        />
      )}
    </div>
  );
}

function AddCustomFields({ sectionKey, onAddField, disabled }) {
  const [newLabel, setNewLabel] = useState("");
  const [newType, setNewType] = useState("text");

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-dashed border-zinc-300 bg-white/30 p-4 dark:border-zinc-700 dark:bg-zinc-900/20">
      <p className="text-sm font-semibold text-zinc-600 dark:text-zinc-300">Add custom field</p>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="w-full sm:min-w-[200px] flex-1">
          <input
            type="text"
            disabled={disabled}
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="Field label"
            className={inputClass}
          />
        </div>
        <div className="w-full sm:w-40 shrink-0">
          <select
            disabled={disabled}
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className={inputClass}
          >
            {FIELD_TYPES.map((ft) => (
              <option key={ft.value} value={ft.value}>
                {ft.label}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={disabled || !newLabel.trim()}
          onClick={() => {
            onAddField(sectionKey, newLabel, newType);
            setNewLabel("");
            setNewType("text");
          }}
          className="flex items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 py-3 text-sm font-semibold text-white shadow transition hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          <Plus className="w-4 h-4" /> Add
        </button>
      </div>
    </div>
  );
}

export default function JournalCreateForm({
  templates = [],
  latestStructure = null,
  onCancel,
  onSubmit,
  onDeleteTemplate,
}) {
  const [localDatetime, setLocalDatetime] = useState("");
  const [ready, setReady] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      setLocalDatetime(toDatetimeLocalValue(new Date()));
      setReady(true);
    });
    return () => cancelAnimationFrame(id);
  }, []);

  const [content, setContent] = useState("");
  const [draftSections, setDraftSections] = useState(() =>
    initialDraftSectionsFromLatest(latestStructure, templates)
  );
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [newCustomSectionReusable, setNewCustomSectionReusable] = useState(true);

  const addFromTemplate = () => {
    const id = selectedTemplateId === "" ? NaN : Number.parseInt(selectedTemplateId, 10);
    const template = templates.find((t) => t.id === id);
    if (!template) return;
    setDraftSections((s) => [...s, sectionFromTemplate(template)]);
    setSelectedTemplateId("");
  };

  const addCustomSection = () => {
    setDraftSections((s) => [
      ...s,
      emptyCustomSection(newCustomSectionReusable),
    ]);
  };

  const setSectionReusable = (clientKey, reusable) => {
    setDraftSections((s) =>
      s.map((sec) => (sec.clientKey === clientKey ? { ...sec, reusable } : sec))
    );
  };

  const removeSection = (clientKey) => {
    setDraftSections((s) => s.filter((x) => x.clientKey !== clientKey));
  };

  const setSectionName = (clientKey, name) => {
    setDraftSections((s) =>
      s.map((sec) => (sec.clientKey === clientKey ? { ...sec, name } : sec))
    );
  };

  const setFieldValue = (clientKey, fieldIndex, value) => {
    setDraftSections((s) =>
      s.map((sec) =>
        sec.clientKey !== clientKey
          ? sec
          : {
            ...sec,
            fieldValues: sec.fieldValues.map((fv, i) =>
              i === fieldIndex ? { ...fv, value } : fv
            ),
          }
      )
    );
  };

  const addCustomField = (clientKey, label, field_type) => {
    const trimmed = label.trim();
    if (!trimmed) return;
    setDraftSections((s) =>
      s.map((sec) =>
        sec.clientKey !== clientKey
          ? sec
          : {
            ...sec,
            fieldValues: [
              ...sec.fieldValues,
              {
                templateFieldId: undefined,
                label: trimmed,
                field_type,
                value: field_type === "checkbox" ? "false" : "",
              },
            ],
          }
      )
    );
  };

  const removeCustomField = (clientKey, fieldIndex) => {
    setDraftSections((s) =>
      s.map((sec) =>
        sec.clientKey !== clientKey
          ? sec
          : {
            ...sec,
            fieldValues: sec.fieldValues.filter((_, i) => i !== fieldIndex),
          }
      )
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedContent = content.trim();
    if (!trimmedContent && draftSections.length === 0) return;
    if (!ready || !localDatetime) return;
    const date = new Date(localDatetime);
    if (Number.isNaN(date.getTime())) return;

    const sections = draftSections.map((s) => ({
      name: s.name,
      templateId: s.templateId,
      reusable: Boolean(s.reusable),
      fieldValues: s.fieldValues.map((fv) => ({
        label: fv.label,
        field_type: fv.field_type,
        value: fv.value,
        field_id: fv.templateFieldId,
      })),
    }));

    try {
      setIsSubmitting(true);
      await onSubmit({
        date: localDatetime.length === 16 ? `${localDatetime}:00` : localDatetime,
        content: trimmedContent,
        sections,
      });
    } catch (err) {
      console.error(err);
      setIsSubmitting(false); // Stop loading if failed
    }
  };

  const canSubmit =
    ready &&
    !!localDatetime &&
    (content.trim().length > 0 || draftSections.length > 0);

  return (
    <motion.form
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      onSubmit={handleSubmit}
      className={cn("space-y-6 pb-12", isSubmitting && "opacity-80 pointer-events-none")}
    >
      <div className="flex items-center gap-3 mb-6">
        <button
          type="button"
          disabled={isSubmitting}
          onClick={onCancel}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-zinc-200 bg-white/80 px-4 py-2 text-sm font-bold text-zinc-800 shadow-sm transition-all hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/80 dark:text-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-50"
        >
          <X className="w-4 h-4" />
          Cancel
        </button>
      </div>

      <div className="space-y-6">
        <div>
          <label htmlFor="journal-date" className={labelClass}>
            Date & Time
          </label>
          <input
            id="journal-date"
            type="datetime-local"
            value={localDatetime}
            onChange={(e) => setLocalDatetime(e.target.value)}
            disabled={!ready || isSubmitting}
            className={cn(inputClass, "max-w-md")}
          />
        </div>

        <div>
          <label htmlFor="journal-content" className={labelClass}>
            Entry <span className="lowercase font-medium tracking-normal ml-1">(Optional if adding sections)</span>
          </label>
          <textarea
            id="journal-content"
            rows={6}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={isSubmitting}
            placeholder="What's on your mind?"
            className={cn(inputClass, "resize-y placeholder:text-zinc-400 dark:placeholder:text-zinc-500 font-medium leading-relaxed")}
          />
        </div>
      </div>

      <div className="pt-4 space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Structure
          </h3>
          <div className="flex flex-wrap items-center gap-3">
            {templates.length > 0 && (
              <div className="flex items-center bg-white/50 dark:bg-zinc-900/50 p-1 rounded-xl border border-zinc-200 dark:border-zinc-800">
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  disabled={isSubmitting}
                  className="bg-transparent text-sm font-medium border-none outline-none dark:text-zinc-200 px-3 py-1 cursor-pointer"
                >
                  <option value="">Add from template…</option>
                  {templates.map((t) => (
                    <option key={t.id} value={String(t.id)}>
                      {t.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addFromTemplate}
                  disabled={selectedTemplateId === "" || isSubmitting}
                  className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-zinc-700 disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
                >
                  Insert
                </button>
                {onDeleteTemplate && (
                  <button
                    type="button"
                    onClick={async () => {
                      if (window.confirm("Make this template inactive? You won't be able to insert it again.")) {
                        try {
                          setIsSubmitting(true);
                          await onDeleteTemplate(selectedTemplateId);
                          setSelectedTemplateId("");
                        } catch (err) {
                          console.error(err);
                        } finally {
                          setIsSubmitting(false);
                        }
                      }
                    }}
                    disabled={selectedTemplateId === "" || isSubmitting}
                    className="flex shrink-0 items-center justify-center rounded-lg bg-red-50 hover:bg-red-100 ml-1 px-2 py-1.5 text-red-600 transition disabled:opacity-50 dark:bg-red-950/30 dark:hover:bg-red-900/40 dark:text-red-400"
                    title="Remove template"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}

            <div className="flex items-center gap-3 bg-white/50 dark:bg-zinc-900/50 py-1 pl-3 pr-1 rounded-xl border border-zinc-200 dark:border-zinc-800">
              <label className="flex cursor-pointer items-center gap-2 text-xs font-bold text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                <input
                  type="checkbox"
                  checked={newCustomSectionReusable}
                  disabled={isSubmitting}
                  onChange={(e) => setNewCustomSectionReusable(e.target.checked)}
                  className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600 disabled:opacity-50"
                />
                Reusable
              </label>
              <button
                type="button"
                onClick={addCustomSection}
                disabled={isSubmitting}
                className="flex items-center gap-1 rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-zinc-800 dark:bg-emerald-600 dark:text-emerald-50 dark:hover:bg-emerald-500 disabled:opacity-50"
              >
                <Plus className="w-3.5 h-3.5" /> Custom
              </button>
            </div>
          </div>
        </div>

        {draftSections.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-300 bg-white/30 px-6 py-12 text-center dark:border-zinc-800 dark:bg-zinc-900/20">
            <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
              No sections active. Use a template or build your own custom structure above.
            </p>
          </div>
        ) : (
          <motion.div layout className="flex flex-col gap-6 pt-2">
            <AnimatePresence>
              {draftSections.map((sec) => (
                <motion.article
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  key={sec.clientKey}
                  className="group relative rounded-3xl border border-zinc-200 bg-white/60 p-6 shadow-sm backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/50"
                >
                  <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
                    <div className="flex-1 space-y-2 w-full">
                      {sec.templateId != null ? (
                        <div className="flex items-center gap-4">
                          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                            Template
                          </span>
                          <label className="flex cursor-pointer items-center gap-2 text-xs font-bold text-zinc-600 dark:text-zinc-400">
                            <input
                              type="checkbox"
                              checked={sec.reusable !== false}
                              disabled={isSubmitting}
                              onChange={(e) => setSectionReusable(sec.clientKey, e.target.checked)}
                              className="h-3.5 w-3.5 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600 disabled:opacity-50"
                            />
                            Reusable
                          </label>
                        </div>
                      ) : (
                        <div className="flex items-center gap-4">
                          <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-purple-800 dark:bg-purple-950/50 dark:text-purple-400 border border-purple-200 dark:border-purple-800">
                            Custom
                          </span>
                          <label className="flex cursor-pointer items-center gap-2 text-xs font-bold text-zinc-600 dark:text-zinc-400">
                            <input
                              type="checkbox"
                              checked={sec.reusable !== false}
                              disabled={isSubmitting}
                              onChange={(e) => setSectionReusable(sec.clientKey, e.target.checked)}
                              className="h-3.5 w-3.5 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600 disabled:opacity-50"
                            />
                            Save as template
                          </label>
                        </div>
                      )}

                      <div className="mt-2 w-full max-w-lg">
                        <label className="sr-only" htmlFor={`name-${sec.clientKey}`}>
                          Section Title
                        </label>
                        <input
                          id={`name-${sec.clientKey}`}
                          type="text"
                          value={sec.name}
                          disabled={isSubmitting}
                          onChange={(e) => setSectionName(sec.clientKey, e.target.value)}
                          placeholder="Section Title"
                          className="w-full text-xl font-bold bg-transparent outline-none placeholder:text-zinc-400 text-zinc-900 dark:text-zinc-100 border-b-2 border-transparent focus:border-zinc-300 dark:focus:border-zinc-700 transition-colors pb-1"
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => removeSection(sec.clientKey)}
                      className="shrink-0 p-2 text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 rounded-xl transition-all disabled:opacity-50"
                      title="Remove section"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="flex flex-col gap-4">
                    {sec.fieldValues.map((fv, idx) =>
                      sec.templateId != null ? (
                        <TemplateFieldRow
                          key={`${sec.clientKey}-f-${idx}`}
                          fv={fv}
                          fieldIndex={idx}
                          disabled={isSubmitting}
                          onChange={(i, v) => setFieldValue(sec.clientKey, i, v)}
                        />
                      ) : (
                        <CustomFieldRow
                          key={`${sec.clientKey}-custom-${idx}`}
                          fv={fv}
                          fieldIndex={idx}
                          disabled={isSubmitting}
                          onChange={(i, v) => setFieldValue(sec.clientKey, i, v)}
                          onRemove={(i) => removeCustomField(sec.clientKey, i)}
                        />
                      )
                    )}
                  </div>

                  {sec.templateId == null && (
                    <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
                      <AddCustomFields
                        sectionKey={sec.clientKey}
                        onAddField={addCustomField}
                        disabled={isSubmitting}
                      />
                    </div>
                  )}
                </motion.article>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      <div className="flex justify-end pt-8">
        <button
          type="submit"
          disabled={!canSubmit || isSubmitting}
          className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-zinc-900 px-8 py-4 text-base font-bold text-white shadow-lg transition-all hover:bg-zinc-800 hover:shadow-xl hover:-translate-y-0.5 active:scale-95 disabled:pointer-events-none disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
        >
          {isSubmitting ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Saving Journal...</>
          ) : (
            "Save Entry"
          )}
        </button>
      </div>
    </motion.form>
  );
}