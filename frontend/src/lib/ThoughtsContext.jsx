"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api from "./api";
import { useAuth } from "./AuthContext";

const ThoughtsContext = createContext(null);

export function ThoughtsProvider({ children }) {
    const [thoughts, setThoughts] = useState([]);
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);

    // Fetch thoughts on mount if authenticated
    useEffect(() => {
        if (user) {
            fetchThoughts();
        } else {
            setThoughts([]);
        }
    }, [user]);

    const fetchThoughts = async () => {
        try {
            setLoading(true);
            const res = await api.get("/api/v1/thoughts");
            // ensure descending order
            const sorted = res.data.sort((a, b) => b.id - a.id);
            setThoughts(sorted);
        } catch (err) {
            console.error("Failed to fetch thoughts:", err);
        } finally {
            setLoading(false);
        }
    };

    const addThought = useCallback(async ({ title, content }) => {
        try {
            const res = await api.post("/api/v1/thoughts", {
                title: (title || "").trim(),
                content: (content || "").trim()
            });
            // Pushing to top locally for snappy UI
            setThoughts((prev) => [res.data, ...prev]);
        } catch (err) {
            console.error("Failed to add thought:", err);
            throw err;
        }
    }, []);

    const editThought = useCallback(async (id, { title, content }) => {
        try {
            const res = await api.patch(`/api/v1/thoughts/${id}`, {
                id,
                title: (title || "").trim(),
                content: (content || "").trim()
            });
            setThoughts((prev) =>
                prev.map((t) => (t.id === id ? res.data.thought || res.data : t))
            );
        } catch (err) {
            console.error("Failed to edit thought:", err);
        }
    }, []);

    const deleteThought = useCallback(async (id) => {
        try {
            await api.delete(`/api/v1/thoughts/${id}`);
            setThoughts((prev) => prev.filter((t) => t.id !== id));
        } catch (err) {
            console.error("Failed to delete thought:", err);
        }
    }, []);

    const value = useMemo(
        () => ({
            thoughts,
            loading,
            addThought,
            editThought,
            deleteThought,
            refreshThoughts: fetchThoughts
        }),
        [thoughts, loading, addThought, editThought, deleteThought]
    );

    return (
        <ThoughtsContext.Provider value={value}>
            {children}
        </ThoughtsContext.Provider>
    );
}

export function useThoughts() {
    const context = useContext(ThoughtsContext);
    if (!context) {
        throw new Error("useThoughts must be used within a ThoughtsProvider");
    }
    return context;
}
