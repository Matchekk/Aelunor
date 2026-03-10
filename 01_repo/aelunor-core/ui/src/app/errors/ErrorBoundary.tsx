import type { ErrorInfo, ReactNode } from "react";
import { Component } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      message: "",
    };
  }

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || "Unexpected application error",
    };
  }

  public componentDidCatch(_error: Error, _errorInfo: ErrorInfo): void {
    // Reserved for client-side error reporting integration.
  }

  public render() {
    if (!this.state.hasError) {
      return this.props.children;
    }
    return (
      <main className="app-shell-message">
        <h1>UI v1 Error</h1>
        <p>{this.state.message}</p>
      </main>
    );
  }
}
