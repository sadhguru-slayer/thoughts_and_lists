/** Seed data matching GET /journals and GET /journal/{id} response shapes. */

/**
 * GET /journal/structure/latest response shape — sections from the user’s last entry,
 * fields with values cleared for a new draft.
 */
export function buildLatestStructureFromTemplates(templates) {
  return {
    sections: templates.map((t) => ({
      name: t.name,
      template_id: t.id,
      fields: [...t.fields]
        .sort((a, b) => a.order - b.order)
        .map((f) => ({
          label: f.label,
          field_type: f.field_type,
          value: null,
        })),
    })),
  };
}

/** GET /templates — section definitions for scaffolded journal sections */
export const initialSectionTemplates = [
  {
    id: 1,
    name: "Morning Reflection",
    description: "How you start the day",
    status: "active",
    fields: [
      {
        id: 101,
        label: "How did I feel this morning?",
        field_type: "text",
        placeholder: "",
        required: false,
        order: 0,
      },
      {
        id: 102,
        label: "Main goal for today",
        field_type: "text",
        placeholder: "",
        required: false,
        order: 1,
      },
    ],
  },
  {
    id: 2,
    name: "Work Progress",
    description: "What moved at work",
    status: "active",
    fields: [
      {
        id: 201,
        label: "What did you accomplish?",
        field_type: "textarea",
        placeholder: "",
        required: false,
        order: 0,
      },
      {
        id: 202,
        label: "Any blockers?",
        field_type: "text",
        placeholder: "",
        required: false,
        order: 1,
      },
    ],
  },
  {
    id: 3,
    name: "Daily Habits",
    description: "Quick checks",
    status: "active",
    fields: [
      {
        id: 301,
        label: "Did you exercise?",
        field_type: "checkbox",
        placeholder: "",
        required: false,
        order: 0,
      },
      {
        id: 302,
        label: "Did you read today?",
        field_type: "checkbox",
        placeholder: "",
        required: false,
        order: 1,
      },
    ],
  },
];

export const initialJournals = [
  {
    date: "2026-03-22T08:00:00",
    content: "Daily reflection and work updates.",
    id: 8,
    user_id: 1,
    created_at: "2026-03-22T08:05:00.000000Z",
  },
  {
    date: "2026-03-21T18:30:00",
    content: "Reflecting on my day and planning ahead.",
    id: 6,
    user_id: 1,
    created_at: "2026-03-21T18:41:53.287843Z",
  },
  {
    date: "2026-03-21T10:00:00",
    content: "Today was a calm and productive day.",
    id: 7,
    user_id: 1,
    created_at: "2026-03-21T10:11:00.000000Z",
  },
];

export const initialDetailById = {
  6: {
    id: 6,
    date: "2026-03-21T18:30:00",
    content: "Reflecting on my day and planning ahead.",
    sections: [
      {
        id: 16,
        name: "Morning Reflection",
        template_id: 10,
        field_values: [
          {
            id: 37,
            label: "How did I feel this morning?",
            field_type: "text",
            value: "Energetic and positive",
          },
          {
            id: 38,
            label: "Main goal for today",
            field_type: "text",
            value: "Finish backend optimization",
          },
        ],
      },
      {
        id: 17,
        name: "Work Progress",
        template_id: 11,
        field_values: [
          {
            id: 39,
            label: "What did I accomplish?",
            field_type: "textarea",
            value: "Optimized database queries and improved API performance.",
          },
          {
            id: 40,
            label: "Any blockers?",
            field_type: "text",
            value: "Minor debugging issues",
          },
        ],
      },
      {
        id: 18,
        name: "Daily Habits",
        template_id: 12,
        field_values: [
          {
            id: 41,
            label: "Did I exercise?",
            field_type: "checkbox",
            value: "true",
          },
          {
            id: 42,
            label: "Did I read a book?",
            field_type: "checkbox",
            value: "false",
          },
        ],
      },
    ],
  },
  7: {
    id: 7,
    date: "2026-03-21T10:00:00",
    content: "Today was a calm and productive day.",
    sections: [],
  },
  8: {
    id: 8,
    date: "2026-03-22T08:00:00",
    content: "Daily reflection and work updates.",
    sections: [
      {
        id: 101,
        name: "Morning Reflection",
        template_id: 7,
        field_values: [
          {
            id: 201,
            label: "How did I feel this morning?",
            field_type: "text",
            value: "Motivated and focused",
          },
          {
            id: 202,
            label: "Main goal for today",
            field_type: "text",
            value: "Finish FastAPI journaling module",
          },
        ],
      },
      {
        id: 102,
        name: "Work Progress",
        template_id: 8,
        field_values: [
          {
            id: 203,
            label: "What did I accomplish?",
            field_type: "textarea",
            value: "Deployed optimized queries and added tests",
          },
          {
            id: 204,
            label: "Any blockers?",
            field_type: "text",
            value: "Waiting for API review feedback",
          },
        ],
      },
      {
        id: 103,
        name: "Daily Habits",
        template_id: 9,
        field_values: [
          {
            id: 205,
            label: "Did I exercise?",
            field_type: "checkbox",
            value: "true",
          },
          {
            id: 206,
            label: "Did I read a book?",
            field_type: "checkbox",
            value: "false",
          },
        ],
      },
    ],
  },
};

export function sortJournalsDescByDate(list) {
  return [...list].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
}

/**
 * Turn create-form drafts into GET /journal/:id shaped sections with synthetic ids.
 */
export function buildDetailSectionsFromDrafts(drafts) {
  const t = Date.now();
  return drafts.map((d, si) => {
    const sectionId = t + si * 10_000;
    return {
      id: sectionId,
      name: d.name?.trim() || "Untitled section",
      template_id: d.templateId,
      field_values: d.fieldValues.map((fv, fi) => ({
        id: sectionId + fi + 1,
        label: fv.label,
        field_type: fv.field_type,
        value:
          fv.field_type === "checkbox"
            ? fv.value === "true" || fv.value === true
              ? "true"
              : "false"
            : (fv.value ?? "") === ""
              ? null
              : String(fv.value),
      })),
    };
  });
}

export function cloneInitialState() {
  return {
    journals: sortJournalsDescByDate(initialJournals),
    detailById: structuredClone(initialDetailById),
  };
}
