import { Component } from "react"
import type { ErrorInfo, ReactNode } from "react"
import { Button } from "@/components/ui/button"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-svh flex-col items-center justify-center gap-4 p-6 text-center">
          <div className="text-destructive text-4xl">Something went wrong</div>
          <p className="text-muted-foreground max-w-md text-sm">
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <Button
            variant="outline"
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.href = "/"
            }}
          >
            Back to Home
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
