import { createBrowserRouter } from 'react-router-dom'
import { ErrorPage } from '@/pages/errors/ErrorPage'
import { LandingPage } from '@/pages/LandingPage'
import { AppShell } from '@/pages/AppShell'
import { BuildsPage } from '@/pages/BuildsPage'
import { CatalogPage } from '@/pages/CatalogPage'
import { ChatPage } from '@/pages/ChatPage'
import { AdminUsersPage } from '@/pages/AdminUsersPage'
import { RequireAuth } from './guards/RequireAuth'
import { RequireAdmin } from './guards/RequireAdmin'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
    errorElement: <ErrorPage />,
  },
  {
    path: '/app',
    element: <RequireAuth />,
    errorElement: <ErrorPage />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <BuildsPage /> },
          { path: 'catalog', element: <CatalogPage /> },
          { path: 'chat', element: <ChatPage /> },
          {
            path: 'admin',
            element: <RequireAdmin />,
            children: [{ path: 'users', element: <AdminUsersPage /> }],
          },
        ],
      },
    ],
  },
])