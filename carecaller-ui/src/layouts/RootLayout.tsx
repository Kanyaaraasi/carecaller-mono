import { Outlet } from "@tanstack/react-router"
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools"
import { Toaster } from "@/components/ui/sonner"

export function RootLayout() {
  return (
    <div className="flex min-h-svh flex-col">
      <Outlet />
      <Toaster position="bottom-right" />
      {import.meta.env.DEV && <TanStackRouterDevtools position="bottom-right" />}
    </div>
  )
}
