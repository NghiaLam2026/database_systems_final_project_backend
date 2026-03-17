import { isRouteErrorResponse, useRouteError } from 'react-router-dom'

export function ErrorPage() {
  const err = useRouteError()

  const title = 'Something went wrong'
  let message = 'An unexpected error occurred.'

  if (isRouteErrorResponse(err)) {
    message = `${err.status} ${err.statusText}`
  } else if (err instanceof Error) {
    message = err.message
  }

  return (
    <div className="min-h-screen bg-hero">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="rounded-xl2 bg-white/80 p-10 shadow-card backdrop-blur">
          <h1 className="text-2xl font-semibold text-ink-950">{title}</h1>
          <p className="mt-2 text-sm text-ink-800">{message}</p>
          <a
            className="mt-6 inline-flex rounded-xl bg-ink-950 px-4 py-2 text-sm font-medium text-white hover:bg-ink-900"
            href="/"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  )
}