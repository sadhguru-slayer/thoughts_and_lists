"use client";

import { useJournal } from "@/lib/JournalContext";
import JournalList from "@/components/journal/JournalList";

export default function Home() {
  const { journals } = useJournal();

  return <JournalList journals={journals} />;
}
