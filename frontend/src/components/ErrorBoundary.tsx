import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ErrorBoundaryState {
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('UI ErrorBoundary caught', error, info);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  override render(): ReactNode {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-bg-0 px-6 text-center">
          <AlertTriangle className="h-12 w-12 text-accent" aria-hidden />
          <div className="space-y-2">
            <h1 className="font-display text-3xl font-bold tracking-tightest text-text-0">
              Something went wrong.
            </h1>
            <p className="max-w-md text-sm text-text-1">
              {this.state.error.message || 'An unexpected error occurred while rendering the page.'}
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="primary" onClick={this.reset}>
              Try again
            </Button>
            <Button variant="ghost" onClick={() => window.location.assign('/')}>
              Back to browse
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
