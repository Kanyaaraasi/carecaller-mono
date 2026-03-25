import { createRouter, createRoute, createRootRoute } from "@tanstack/react-router"
import { RootLayout } from "./layouts/RootLayout"
import { PatientSetup } from "./pages/PatientSetup"
import { ActiveCall } from "./pages/ActiveCall"
import { CallSummary } from "./pages/CallSummary"

const rootRoute = createRootRoute({
  component: RootLayout,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: PatientSetup,
})

const callRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/call/$callId",
  component: ActiveCall,
})

const summaryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/call/$callId/summary",
  component: CallSummary,
})

const routeTree = rootRoute.addChildren([indexRoute, callRoute, summaryRoute])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
