"use client";

import ThoughtInput from "@/components/thoughts/ThoughtInput";
import ThoughtCard from "@/components/thoughts/ThoughtCard";
import { useThoughts } from "@/lib/ThoughtsContext";
import { AnimatePresence } from "framer-motion";

export default function ThoughtsPage() {
    const { thoughts } = useThoughts();

    return (
        <div className="w-full flex-1 pt-6 px-4 md:px-0">
            <ThoughtInput />

            <div className="columns-1 sm:columns-2 lg:columns-3 gap-4 space-y-4">
                <AnimatePresence>
                    {thoughts.map((thought) => (
                        <div key={thought.id} className="break-inside-avoid">
                            <ThoughtCard thought={thought} />
                        </div>
                    ))}
                </AnimatePresence>
            </div>

            {thoughts.length === 0 && (
                <div className="text-center mt-20 text-zinc-500 dark:text-zinc-400 font-medium">
                    Take a moment to jot down a thought.
                </div>
            )}
        </div>
    );
}
