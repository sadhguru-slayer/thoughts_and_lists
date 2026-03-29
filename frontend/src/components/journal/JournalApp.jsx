"use client";

import { useCallback, useMemo, useState } from "react";
import {
  buildDetailSectionsFromDrafts,
  cloneInitialState,
  initialSectionTemplates,
  sortJournalsDescByDate,
} from "@/lib/journalMock";
import JournalCreateForm from "./JournalCreateForm";
import JournalDetail from "./JournalDetail";
import JournalList from "./JournalList";

export default function JournalApp() {
  const [journals, setJournals] = useState(() => cloneInitialState().journals);
  const [detailById, setDetailById] = useState(
    () => cloneInitialState().detailById,
  );
  const [view, setView] = useState("list");
  const [selectedId, setSelectedId] = useState(null);
  const [templates] = useState(() => structuredClone(initialSectionTemplates));

  const journalsForList = useMemo(
    () =>
      journals.map((j) => ({
        ...j,
        sectionCount: detailById[j.id]?.sections?.length ?? 0,
      })),
    [journals, detailById],
  );

  const getNextId = useCallback(() => {
    const ids = journals.map((j) => j.id);
    return (ids.length ? Math.max(...ids) : 0) + 1;
  }, [journals]);

  const goList = useCallback(() => {
    setView("list");
    setSelectedId(null);
  }, []);

  const openDetail = useCallback((id) => {
    setSelectedId(id);
    setView("detail");
  }, []);

  const openCreate = useCallback(() => {
    setSelectedId(null);
    setView("create");
  }, []);

  const handleCreateSubmit = useCallback(
    ({ date, content, sections: sectionDrafts }) => {
      const id = getNextId();
      const created_at = new Date().toISOString();
      const sections = buildDetailSectionsFromDrafts(sectionDrafts ?? []);
      const contentNorm = (content ?? "").trim();
      const row = {
        id,
        date,
        content: contentNorm || null,
        user_id: 1,
        created_at,
      };
      setJournals((prev) => sortJournalsDescByDate([...prev, row]));
      setDetailById((prev) => ({
        ...prev,
        [id]: {
          id,
          date,
          content: contentNorm,
          sections,
        },
      }));
      goList();
    },
    [goList, getNextId],
  );

  const handleDelete = useCallback(
    (id) => {
      setJournals((prev) => prev.filter((j) => j.id !== id));
      setDetailById((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      goList();
    },
    [goList],
  );

  const detail =
    selectedId != null ? (detailById[selectedId] ?? null) : null;

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 dark:bg-zinc-950">
      <header className="shrink-0 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Journal
          </h1>
          {view !== "create" && (
            <button
              type="button"
              onClick={openCreate}
              className="inline-flex items-center rounded-lg bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 dark:focus-visible:ring-zinc-500 dark:focus-visible:ring-offset-zinc-950"
            >
              New journal
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-6 sm:px-6">
        <div
          key={`${view}-${selectedId ?? ""}`}
          className="journal-panel-enter"
        >
          {view === "list" && (
            <JournalList journals={journalsForList} onSelect={openDetail} />
          )}
          {view === "detail" && detail && (
            <JournalDetail
              detail={detail}
              onBack={goList}
              onDelete={handleDelete}
            />
          )}
          {view === "create" && (
            <JournalCreateForm
              templates={templates}
              onCancel={goList}
              onSubmit={handleCreateSubmit}
            />
          )}
        </div>
      </main>
    </div>
  );
}
