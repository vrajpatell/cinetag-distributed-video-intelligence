import { API_BASE_URL } from '@/lib/api';

const endpoints = [
  ['GET', '/health', 'Check whether the API process is running.'],
  ['GET', '/ready', 'Check whether the API can reach its database.'],
  ['GET', '/api/videos', 'List videos in the private library.'],
  ['GET', '/api/videos/{video_id}/transcript', 'Read the transcript for a video.'],
  ['GET', '/api/jobs', 'Inspect processing jobs.'],
  ['GET', '/api/review', 'List tags that need editorial review.'],
  ['POST', '/api/search/semantic', 'Search videos by meaning.'],
  ['GET', '/api/catalog/schema', 'List catalog datasets, fields, and supported filters.'],
];

export default function ApiDocs() {
  return (
    <article className="mx-auto max-w-4xl space-y-7 px-5 py-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">CineTag API reference</h1>
        <p className="text-white/70">
          Health and readiness are public. For private routes, send your assigned API key in the
          <code> X-API-Key </code> header from a trusted client. Writes require the appropriate role.
        </p>
      </header>
      <section aria-labelledby="connection" className="panel space-y-2 p-5">
        <h2 id="connection" className="text-lg font-semibold">API connection</h2>
        {API_BASE_URL ? (
          <>
            <p className="break-all font-mono">{API_BASE_URL}</p>
            <p className="text-white/70">
              Authenticated clients can request <code>/openapi.json</code> on this host for the complete schema.
            </p>
          </>
        ) : (
          <p className="text-white/70">This public demo has no backend URL configured. The endpoints below
            apply to a connected CineTag backend.</p>
        )}
      </section>
      <section aria-labelledby="routes">
        <h2 id="routes" className="mb-3 text-lg font-semibold">Common endpoints</h2>
        <dl className="divide-y divide-white/10">
          {endpoints.map(([method, path, description]) => (
            <div key={path} className="py-3">
              <dt className="break-all font-mono text-sm">{method} {path}</dt>
              <dd className="mt-1 text-sm text-white/65">{description}</dd>
            </div>
          ))}
        </dl>
      </section>
    </article>
  );
}
