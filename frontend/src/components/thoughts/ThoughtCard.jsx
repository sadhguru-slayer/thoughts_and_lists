"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Trash2, Edit2 } from "lucide-react";
import { useThoughts } from "@/lib/ThoughtsContext";
import { cn } from "@/lib/utils";

export default function ThoughtCard({ thought }) {
    const { deleteThought, editThought } = useThoughts();
    const [isEditing, setIsEditing] = useState(false);
    const [title, setTitle] = useState(thought.title);
    const [content, setContent] = useState(thought.content);

    const handleSave = () => {
        editThought(thought.id, { title, content });
        setIsEditing(false);
    };

    if (isEditing) {
        return (
            <motion.div
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="group relative flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-4 shadow-xl ring-1 ring-zinc-200 dark:border-zinc-800 dark:bg-zinc-900 dark:ring-zinc-700"
            >
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full text-base font-semibold bg-transparent border-none outline-none placeholder:text-zinc-500 text-zinc-900 dark:text-zinc-100"
                    placeholder="Title"
                    autoFocus
                />
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full text-sm bg-transparent border-none outline-none resize-none placeholder:text-zinc-500 text-zinc-900 dark:text-zinc-100 leading-relaxed font-medium min-h-[80px]"
                    placeholder="Take a note..."
                />
                <div className="flex justify-end gap-2 mt-2">
                    <button
                        onClick={() => setIsEditing(false)}
                        className="text-xs font-semibold tracking-wide text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 px-3 py-1.5 rounded-lg transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        className="text-xs font-semibold tracking-wide bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 px-4 py-1.5 rounded-lg transition-colors shadow-sm hover:shadow-md active:scale-95"
                    >
                        Save
                    </button>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            whileHover={{ y: -2 }}
            className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm transition-all hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
        >
            {thought.title && (
                <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight leading-snug">
                    {thought.title}
                </h3>
            )}
            {thought.content && (
                <p className="text-sm text-zinc-600 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">
                    {thought.content}
                </p>
            )}

            {/* Action buttons appear on hover desktop / always flex mobile */}
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 bg-white/80 dark:bg-zinc-900/80 backdrop-blur rounded-lg p-1 shadow-sm border border-zinc-200 dark:border-zinc-800">
                <button
                    onClick={() => setIsEditing(true)}
                    className="p-1.5 text-zinc-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    aria-label="Edit"
                >
                    <Edit2 className="w-3.5 h-3.5" />
                </button>
                <button
                    onClick={() => deleteThought(thought.id)}
                    className="p-1.5 text-zinc-500 hover:text-red-600 dark:hover:text-red-400 transition-colors rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    aria-label="Delete"
                >
                    <Trash2 className="w-3.5 h-3.5" />
                </button>
            </div>
        </motion.div>
    );
}
