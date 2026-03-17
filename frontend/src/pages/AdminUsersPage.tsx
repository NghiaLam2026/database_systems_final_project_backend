export function AdminUsersPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold text-ink-950">Admin · Users</h1>
      <p className="mt-2 text-sm text-ink-800">
        Next: wire admin user list and role assignment to{' '}
        <code className="rounded bg-white px-1 py-0.5">/api/v1/users</code> and{' '}
        <code className="rounded bg-white px-1 py-0.5">/api/v1/users/:id/role</code>.
      </p>
    </div>
  )
}