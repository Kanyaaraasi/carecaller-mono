import { Outlet } from "@tanstack/react-router"
import { Toaster } from "@/components/ui/sonner"
import { ErrorBoundary } from "@/components/ErrorBoundary"

export function RootLayout() {
  return (
    <ErrorBoundary>
      <div className="flex min-h-svh flex-col">
        <Outlet />
        <Toaster position="bottom-right" />
      </div>
    </ErrorBoundary>
  )
}
