"use client";

import { useEffect, useState } from "react";

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
    fieldValues: fields.map((f) => ({
      templateFieldId: f.id,
      label: f.label,
      field_type: f.field_type,
      value: f.field_type === "checkbox" ? "false" : "",
    })),
  };
}

function emptyCustomSection() {
  return {
    clientKey: newClientKey(),
    templateId: null,
    name: "",
    fieldValues: [],
  };
}

const FIELD_TYPES = [
  { value: "text", label: "Short text" },
  { value: "textarea", label: "Long text" },
  { value: "checkbox", label: "Checkbox" },
];

const inputClass =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm focus-visible:border-zinc-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:focus-visible:ring-zinc-500";

const labelClass =
  "text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400";

function CustomFieldRow({ fieldIndex, fv, onChange, onRemove }) {
  if (fv.field_type === "checkbox") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-100 bg-zinc-50/80 px-3 py-2 dark:border-zinc-800 dark:bg-zinc-800/40">
        <span className="text-sm text-zinc-800 dark:text-zinc-200">
          {fv.label}
        </span>
        <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={fv.value === "true" || fv.value === true}
            onChange={(e) =>
              onChange(fieldIndex, e.target.checked ? "true" : "false")
            }
            className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600"
          />
        </label>
        <button
          type="button"
          onClick={() => onRemove(fieldIndex)}
          className="text-xs font-medium text-red-600 hover:underline dark:text-red-400"
        >
          Remove
        </button>
      </div>
    );
  }

  if (fv.field_type === "textarea") {
    return (
      <div className="space-y-1">
        <div className="flex items-start justify-between gap-2">
          <label className={`${labelClass} normal-case`}>{fv.label}</label>
          <button
            type="button"
            onClick={() => onRemove(fieldIndex)}
            className="shrink-0 text-xs font-medium text-red-600 hover:underline dark:text-red-400"
          >
            Remove
          </button>
        </div>
        <textarea
          rows={3}
          value={fv.value ?? ""}
          onChange={(e) => onChange(fieldIndex, e.target.value)}
          className={inputClass}
        />
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-start justify-between gap-2">
        <label className={`${labelClass} normal-case`}>{fv.label}</label>
        <button
          type="button"
          onClick={() => onRemove(fieldIndex)}
          className="shrink-0 text-xs font-medium text-red-600 hover:underline dark:text-red-400"
        >
          Remove
        </button>
      </div>
      <input
        type="text"
        value={fv.value ?? ""}
        onChange={(e) => onChange(fieldIndex, e.target.value)}
        className={inputClass}
      />
    </div>
  );
}

function TemplateFieldRow({ fv, fieldIndex, onChange }) {
  if (fv.field_type === "checkbox") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-100 bg-zinc-50/80 px-3 py-2 dark:border-zinc-800 dark:bg-zinc-800/40">
        <span className="text-sm text-zinc-800 dark:text-zinc-200">
          {fv.label}
        </span>
        <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={fv.value === "true" || fv.value === true}
            onChange={(e) =>
              onChange(fieldIndex, e.target.checked ? "true" : "false")
            }
            className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-400 dark:border-zinc-600"
          />
        </label>
      </div>
    );
  }

  if (fv.field_type === "textarea") {
    return (
      <div className="space-y-1">
        <label className={`${labelClass} normal-case`}>{fv.label}</label>
        <textarea
          rows={3}
          value={fv.value ?? ""}
          onChange={(e) => onChange(fieldIndex, e.target.value)}
          className={inputClass}
        />
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <label className={`${labelClass} normal-case`}>{fv.label}</label>
      <input
        type="text"
        value={fv.value ?? ""}
        onChange={(e) => onChange(fieldIndex, e.target.value)}
        className={inputClass}
      />
    </div>
  );
}

function AddCustomFields({ sectionKey, onAddField }) {
  const [newLabel, setNewLabel] = useState("");
  const [newType, setNewType] = useState("text");

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-dashed border-zinc-200 bg-white/50 p-3 dark:border-zinc-700 dark:bg-zinc-900/30">
      <p className={labelClass}>Add field</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1 space-y-1">
          <label htmlFor={`lbl-${sectionKey}`} className="sr-only">
            Field label
          </label>
          <input
            id={`lbl-${sectionKey}`}
            type="text"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="Field label"
            className={inputClass}
          />
        </div>
        <div className="w-full sm:w-40">
          <label htmlFor={`typ-${sectionKey}`} className="sr-only">
            Field type
          </label>
          <select
            id={`typ-${sectionKey}`}
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
          onClick={() => {
            onAddField(sectionKey, newLabel, newType);
            setNewLabel("");
            setNewType("text");
          }}
          className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-50 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800"
        >
          Add field
        </button>
      </div>
    </div>
  );
}

export default function JournalCreateForm({ templates = [], onCancel, onSubmit }) {
  const [localDatetime, setLocalDatetime] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      setLocalDatetime(toDatetimeLocalValue(new Date()));
      setReady(true);
    });
    return () => cancelAnimationFrame(id);
  }, []);

  const [content, setContent] = useState("");
  const [draftSections, setDraftSections] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");

  const addFromTemplate = () => {
    const id =
      selectedTemplateId === "" ? NaN : Number.parseInt(selectedTemplateId, 10);
    const template = templates.find((t) => t.id === id);
    if (!template) return;
    setDraftSections((s) => [...s, sectionFromTemplate(template)]);
    setSelectedTemplateId("");
  };

  const addCustomSection = () => {
    setDraftSections((s) => [...s, emptyCustomSection()]);
  };

  const removeSection = (clientKey) => {
    setDraftSections((s) => s.filter((x) => x.clientKey !== clientKey));
  };

  const setSectionName = (clientKey, name) => {
    setDraftSections((s) =>
      s.map((sec) => (sec.clientKey === clientKey ? { ...sec, name } : sec)),
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
                i === fieldIndex ? { ...fv, value } : fv,
              ),
            },
      ),
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
            },
      ),
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
            },
      ),
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedContent = content.trim();
    if (!trimmedContent && draftSections.length === 0) return;
    if (!ready || !localDatetime) return;
    const date = new Date(localDatetime);
    if (Number.isNaN(date.getTime())) return;

    const sections = draftSections.map((s) => ({
      name: s.name,
      templateId: s.templateId,
      fieldValues: s.fieldValues.map((fv) => ({
        label: fv.label,
        field_type: fv.field_type,
        value: fv.value,
      })),
    }));

    onSubmit({
      date: date.toISOString(),
      content: trimmedContent,
      sections,
    });
  };

  const canSubmit =
    ready &&
    !!localDatetime &&
    (content.trim().length > 0 || draftSections.length > 0);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800 dark:focus-visible:ring-zinc-500 dark:focus-visible:ring-offset-zinc-950"
        >
          <span aria-hidden>←</span>
          Cancel
        </button>
      </div>

      <div className="space-y-2">
        <label htmlFor="journal-date" className={labelClass}>
          Date & time
        </label>
        <input
          id="journal-date"
          type="datetime-local"
          value={localDatetime}
          onChange={(e) => setLocalDatetime(e.target.value)}
          disabled={!ready}
          className={`${inputClass} max-w-md disabled:opacity-50`}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="journal-content" className={labelClass}>
          Content{" "}
          <span className="font-normal lowercase text-zinc-400">
            (optional if you add sections)
          </span>
        </label>
        <textarea
          id="journal-content"
          rows={8}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your thoughts…"
          className={`${inputClass} resize-y placeholder:text-zinc-400 dark:placeholder:text-zinc-500`}
        />
      </div>

      <section className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h3
            className={`${labelClass} text-left`}
          >
            Sections
          </h3>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            {templates.length > 0 ? (
              <>
                <label htmlFor="pick-template" className="sr-only">
                  Template
                </label>
                <select
                  id="pick-template"
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className={`${inputClass} sm:max-w-xs`}
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
                  disabled={selectedTemplateId === ""}
                  className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm hover:bg-zinc-100 disabled:pointer-events-none disabled:opacity-40 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700"
                >
                  Add section
                </button>
              </>
            ) : (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                No templates — add custom sections below.
              </p>
            )}
            <button
              type="button"
              onClick={addCustomSection}
              className="rounded-lg border border-zinc-900 bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-zinc-800 dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              Custom section
            </button>
          </div>
        </div>

        {draftSections.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No sections yet. Use a template (if available) or add a custom
            section.
          </p>
        ) : (
          <ul className="flex flex-col gap-4">
            {draftSections.map((sec) => (
              <li
                key={sec.clientKey}
                className="rounded-xl border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-700 dark:bg-zinc-800/30"
              >
                <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1 space-y-1">
                    {sec.templateId != null ? (
                      <p className="text-xs font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
                        From template
                      </p>
                    ) : (
                      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                        Custom section
                      </p>
                    )}
                    <label className="sr-only" htmlFor={`name-${sec.clientKey}`}>
                      Section title
                    </label>
                    <input
                      id={`name-${sec.clientKey}`}
                      type="text"
                      value={sec.name}
                      onChange={(e) =>
                        setSectionName(sec.clientKey, e.target.value)
                      }
                      placeholder="Section title"
                      className={inputClass}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => removeSection(sec.clientKey)}
                    className="shrink-0 text-sm font-medium text-red-600 hover:underline dark:text-red-400"
                  >
                    Remove section
                  </button>
                </div>

                <div className="flex flex-col gap-3">
                  {sec.fieldValues.map((fv, idx) =>
                    sec.templateId != null ? (
                      <TemplateFieldRow
                        key={`${sec.clientKey}-f-${idx}`}
                        fv={fv}
                        fieldIndex={idx}
                        onChange={(i, v) => setFieldValue(sec.clientKey, i, v)}
                      />
                    ) : (
                      <CustomFieldRow
                        key={`${fv.label}-${idx}`}
                        sectionKey={sec.clientKey}
                        fv={fv}
                        fieldIndex={idx}
                        onChange={(i, v) =>
                          setFieldValue(sec.clientKey, i, v)
                        }
                        onRemove={(i) =>
                          removeCustomField(sec.clientKey, i)
                        }
                      />
                    ),
                  )}
                </div>

                {sec.templateId == null && (
                  <div className="mt-3">
                    <AddCustomFields
                      sectionKey={sec.clientKey}
                      onAddField={addCustomField}
                    />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 disabled:pointer-events-none disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 dark:focus-visible:ring-zinc-500 dark:focus-visible:ring-offset-zinc-950"
        >
          Save entry
        </button>
      </div>
    </form>
  );
}