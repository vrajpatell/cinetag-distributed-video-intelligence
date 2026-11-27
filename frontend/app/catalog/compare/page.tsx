import Link from 'next/link';
import CompareVideos from '@/components/catalog/CompareVideos';

function videoId(value: string | string[] | undefined) {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const left = videoId(params.left);
  const right = videoId(params.right);
  return (
    <div className="mx-auto max-w-6xl space-y-4 px-5 py-8">
      <Link href="/catalog" className="text-sm underline">
        Catalog workspace
      </Link>
      <h1 className="text-3xl font-bold">Compare videos</h1>
      <CompareVideos initialLeft={left} initialRight={left === right ? null : right} />
    </div>
  );
}
