"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useThoughts } from "@/lib/ThoughtsContext";
import { Plus, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function ThoughtInput() {
    const [isExpanded, setIsExpanded] = useState(false);
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { addThought } = useThoughts();
    const formRef = useRef(null);

    const submitNote = useCallback(async () => {
        if (!title.trim() && !content.trim()) {
            setIsExpanded(false);
            return;
        }

        try {
            setIsSubmitting(true);
            await addThought({ title, content });
            setTitle("");
            setContent("");
            setIsExpanded(false);
        } catch (err) {
            // Error is caught here, keeping input intact.
            console.error(err);
        } finally {
            setIsSubmitting(false);
        }
    }, [title, content, addThought]);

    useEffect(() => {
        async function handleClickOutside(event) {
            if (formRef.current && !formRef.current.contains(event.target)) {
                if (!isSubmitting && (title.trim() || content.trim())) {
                    await submitNote();
                } else {
                    setIsExpanded(false);
                }
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [title, content, isSubmitting, submitNote]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        e.stopPropagation(); // prevent bubbles
        await submitNote();
    };

    return (
        <div className="w-full max-w-xl mx-auto mb-8 relative z-10" ref={formRef}>
            <motion.form
                layout
                onSubmit={handleSubmit}
                className={cn(
                    "bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-3xl shadow-sm overflow-hidden transition-all",
                    isExpanded
                        ? "shadow-xl ring-1 ring-zinc-300 dark:ring-zinc-700"
                        : "hover:shadow-md dark:hover:border-zinc-700"
                )}
            >
                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="px-5 pt-4 pb-2"
                        >
                            <input
                                type="text"
                                placeholder="Title"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                disabled={isSubmitting}
                                className="w-full text-base font-bold bg-transparent border-none outline-none placeholder:text-zinc-400 text-zinc-900 dark:text-zinc-100 disabled:opacity-50"
                                autoFocus
                            />
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className="flex items-start px-5 py-4">
                    <textarea
                        placeholder="Take a note..."
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        onFocus={() => setIsExpanded(true)}
                        disabled={isSubmitting}
                        className={cn(
                            "w-full text-sm bg-transparent border-none outline-none resize-none placeholder:text-zinc-500 text-zinc-900 dark:text-zinc-100 leading-relaxed font-medium disabled:opacity-50",
                            isExpanded ? "min-h-[80px]" : "min-h-[24px]"
                        )}
                    />
                    {!isExpanded && (
                        <button
                            type="button"
                            onClick={() => setIsExpanded(true)}
                            className="p-1.5 rounded-full text-zinc-400 hover:text-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 transition-colors ml-2 shrink-0"
                        >
                            <Plus className="w-5 h-5" />
                        </button>
                    )}
                </div>

                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex justify-between items-center px-3 py-2 bg-zinc-50/50 dark:bg-zinc-900/50 backdrop-blur"
                        >
                            <div className="flex gap-2"></div>
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="flex items-center gap-2 text-sm font-bold tracking-wide text-zinc-900 bg-transparent dark:text-zinc-100 px-4 py-2 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Close"}
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.form>
        </div>
    );
}
