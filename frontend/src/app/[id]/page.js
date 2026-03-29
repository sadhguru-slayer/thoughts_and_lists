"use client";

import { useParams, useRouter } from "next/navigation";
import { useJournal } from "@/lib/JournalContext";
import JournalDetail from "@/components/journal/JournalDetail";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

export default function JournalDetailPage() {
    const router = useRouter();
    const { id } = useParams();
    const { detailById, loadJournalDetail, handleDelete } = useJournal();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchDetail = async () => {
            if (!detailById[id]) {
                await loadJournalDetail(id);
            }
            setIsLoading(false);
        };
        fetchDetail();
    }, [id, detailById, loadJournalDetail]);

    if (isLoading) {
        return (
            <div className="flex justify-center items-center py-20">
                <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
            </div>
        );
    }

    const detail = detailById[id];

    if (!detail) {
        return (
            <div className="py-20 text-center">
                <p className="text-zinc-500 dark:text-zinc-400">Journal not found.</p>
                <button
                    onClick={() => router.push("/")}
                    className="mt-4 text-sm font-medium text-zinc-900 dark:text-zinc-100 hover:underline"
                >
                    Go back home
                </button>
            </div>
        );
    }

    const handleBack = () => {
        router.push("/");
    };

    const onDelete = (journalId) => {
        handleDelete(journalId);
        router.push("/");
    };

    return (
        <JournalDetail
            detail={detail}
            onBack={handleBack}
            onDelete={onDelete}
        />
    );
}
