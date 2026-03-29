"use client";

import { useRouter } from "next/navigation";
import { useJournal } from "@/lib/JournalContext";
import JournalCreateForm from "@/components/journal/JournalCreateForm";

export default function CreateJournalPage() {
    const router = useRouter();
    const { templates, latestJournalStructure, handleCreateSubmit, handleDeleteTemplate } = useJournal();

    const handleCancel = () => {
        router.push("/");
    };

    const handleSubmit = async (data) => {
        await handleCreateSubmit(data);
        router.push("/");
    };

    return (
        <JournalCreateForm
            templates={templates}
            latestStructure={latestJournalStructure}
            onCancel={handleCancel}
            onSubmit={handleSubmit}
            onDeleteTemplate={handleDeleteTemplate}
        />
    );
}
