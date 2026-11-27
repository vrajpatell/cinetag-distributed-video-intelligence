import Link from 'next/link';
import CatalogWorkspace from '@/components/catalog/CatalogWorkspace';

export default function CatalogPage() {
  return (
    <div className="mx-auto max-w-[1400px] space-y-5 px-5 py-8">
      <h1 className="text-3xl font-bold">Catalog workspace</h1>
      <Link className="btn-secondary" href="/catalog/compare">
        Compare videos
      </Link>
      <CatalogWorkspace />
    </div>
  );
}
