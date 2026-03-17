export function ChatPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-ink-950">Chat</h1>
      <p className="mt-2 text-sm text-ink-800">
        Next: wire threads/messages CRUD to{' '}
        <code className="rounded bg-white px-1 py-0.5">/api/v1/threads</code> and{' '}
        <code className="rounded bg-white px-1 py-0.5">/api/v1/threads/:id/messages</code>.
      </p>
    </div>
  )
}