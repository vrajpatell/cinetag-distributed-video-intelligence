import SearchExperience from '@/components/SearchExperience';

export const dynamic = 'force-dynamic';

export default function SearchPage() {
  return (
    <div className="mx-auto max-w-[1400px] space-y-6 px-5 py-8">
      <header className="space-y-2">
        <span className="chip-sky !text-[11px]">
          <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulseSoft" />
          Semantic content discovery
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight md:text-4xl">Find content by meaning</h1>
        <p className="max-w-2xl text-sm text-white/60">
          CineTag indexes tags, transcripts, and multi-modal embeddings, then ranks results by similarity
          to your natural-language query. Each match is explainable and powers downstream recommendation rails.
        </p>
      </header>
      <SearchExperience />
    </div>
  );
}
