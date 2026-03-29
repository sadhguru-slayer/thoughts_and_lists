"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api from "./api";
import { useAuth } from "./AuthContext";

const JournalContext = createContext(null);

export function JournalProvider({ children }) {
    const [journals, setJournals] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [detailById, setDetailById] = useState({});
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (user) {
            fetchJournals();
            fetchTemplates();
        } else {
            setJournals([]);
            setTemplates([]);
            setDetailById({});
        }
    }, [user]);

    const fetchJournals = async () => {
        try {
            setLoading(true);
            const res = await api.get("/api/v1/journals");
            setJournals(res.data);
        } catch (err) {
            console.error("Failed to fetch journals:", err);
        } finally {
            setLoading(false);
        }
    };

    const fetchTemplates = async () => {
        try {
            const res = await api.get("/api/v1/templates");
            setTemplates(res.data);
        } catch (err) {
            console.error("Failed to fetch templates:", err);
        }
    };

    const loadJournalDetail = useCallback(async (id) => {
        try {
            if (detailById[id]) return detailById[id];
            const res = await api.get(`/api/v1/journal/${id}`);
            const detail = res.data;
            console.log(detail)
            setDetailById((prev) => ({ ...prev, [id]: detail }));
            return detail;
        } catch (err) {
            console.error("Failed to fetch journal detail:", err);
            return null;
        }
    }, [detailById]);

    // Builds the starting array for frontend template sections when creating
    const latestJournalStructure = useMemo(
        () => {
            return {
                sections: templates.map((t) => ({
                    name: t.name,
                    template_id: t.id,
                    fields: [...(t.fields || [])]
                        .sort((a, b) => a.order - b.order)
                        .map((f) => ({
                            label: f.label,
                            field_type: f.field_type,
                            value: f.field_type === "checkbox" ? "false" : "",
                        })),
                })),
            };
        },
        [templates]
    );

    const handleCreateSubmit = useCallback(async ({ date, content, sections }) => {
        try {
            const payload = {
                date,
                content: content || null,
                sections: sections.map(s => ({
                    name: s.name,
                    template_id: s.templateId,
                    reusable: s.reusable,
                    field_values: s.fieldValues.map(fv => ({
                        label: fv.label,
                        field_type: fv.field_type,
                        value: fv.value
                    }))
                }))
            };

            const res = await api.post("/api/v1/journal", payload);
            const newJournal = res.data;
            setJournals((prev) => [newJournal, ...prev].sort((a, b) => new Date(b.date) - new Date(a.date)));
            // Also fetch templates again in case they saved a reusable section
            fetchTemplates();
            return newJournal;
        } catch (err) {
            console.error("Failed to create journal:", err);
            throw err; // Let caller Handle errors
        }
    }, []);

    const handleDelete = useCallback(async (id) => {
        try {
            await api.delete(`/api/v1/journal/${id}`);
            setJournals((prev) => prev.filter((j) => j.id !== id));
            setDetailById((prev) => {
                const next = { ...prev };
                delete next[id];
                return next;
            });
        } catch (err) {
            console.error("Failed to delete journal:", err);
        }
    }, []);

    const handleDeleteTemplate = useCallback(async (templateId) => {
        try {
            await api.delete(`/api/v1/templates/${templateId}`);
            setTemplates((prev) => prev.filter(t => String(t.id) !== String(templateId)));
        } catch (err) {
            console.error("Failed to delete template:", err);
            throw err;
        }
    }, []);

    const value = useMemo(
        () => ({
            journals,
            detailById,
            templates,
            latestJournalStructure,
            loading,
            loadJournalDetail,
            handleCreateSubmit,
            handleDelete,
            handleDeleteTemplate,
            refreshJournals: fetchJournals
        }),
        [
            journals,
            detailById,
            templates,
            latestJournalStructure,
            loading,
            loadJournalDetail,
            handleCreateSubmit,
            handleDelete,
            handleDeleteTemplate,
        ]
    );

    return (
        <JournalContext.Provider value={value}>
            {children}
        </JournalContext.Provider>
    );
}

export function useJournal() {
    const context = useContext(JournalContext);
    if (!context) {
        throw new Error("useJournal must be used within a JournalProvider");
    }
    return context;
}
