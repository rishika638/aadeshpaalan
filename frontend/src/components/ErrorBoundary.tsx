import { Component, type ReactNode } from "react";

interface State { error: Error | null }

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-8">
          <div className="border border-risk-overdue/40 rounded-xl bg-risk-overdue/10 p-6 max-w-2xl w-full">
            <div className="text-lg font-semibold text-risk-overdue mb-2">Render Error</div>
            <pre className="text-xs text-slate-300 whitespace-pre-wrap break-all">
              {this.state.error.message}
              {"\n\n"}
              {this.state.error.stack}
            </pre>
            <button
              className="mt-4 px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-sm"
              onClick={() => this.setState({ error: null })}
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
