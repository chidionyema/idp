import React, { Component, ReactNode } from 'react';
import { Box, Paper, Typography, Button } from '@material-ui/core';
import ErrorOutlineIcon from '@material-ui/icons/ErrorOutline';

/**
 * Layer 3 Prevention: Frontend Resilience (Graceful Degradation)
 * Catches component crashes and shows "Feature unavailable" instead of blank page.
 * Logs all errors to analytics for monitoring and alerting.
 *
 * Wraps every major feature to prevent one broken component from breaking the UI.
 */

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  componentName?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });

    const { onError, componentName } = this.props;

    // Log to analytics/monitoring
    try {
      // Send to Datadog/analytics
      if (window.__BACKSTAGE_ANALYTICS__) {
        window.__BACKSTAGE_ANALYTICS__.track('component_crash', {
          component: componentName || 'unknown',
          error: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
        });
      }
    } catch (e) {
      console.error('Failed to log error', e);
    }

    // Call custom error handler if provided
    if (onError) {
      onError(error, errorInfo);
    }

    // Log to console for development
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Paper elevation={0}>
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            p={4}
            minHeight="300px"
            bgcolor="#f5f5f5"
          >
            <ErrorOutlineIcon style={{ fontSize: 48, color: '#d32f2f', marginBottom: 16 }} />
            <Typography variant="h6" gutterBottom style={{ color: '#d32f2f' }}>
              Feature Unavailable
            </Typography>
            <Typography variant="body2" color="textSecondary" align="center" style={{ maxWidth: 400 }}>
              {this.state.error?.message || 'This feature encountered an error and is temporarily unavailable.'}
            </Typography>
            {process.env.NODE_ENV === 'development' && (
              <Box mt={2} p={2} bgcolor="#fff3cd" borderRadius={1} style={{ maxWidth: '100%', overflow: 'auto' }}>
                <Typography variant="caption" component="div" style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {this.state.errorInfo?.componentStack}
                </Typography>
              </Box>
            )}
            <Button
              variant="outlined"
              size="small"
              onClick={() => window.location.reload()}
              style={{ marginTop: 16 }}
            >
              Reload Page
            </Button>
          </Box>
        </Paper>
      );
    }

    return this.props.fallback || this.props.children;
  }
}

/**
 * Hook version for functional components
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  componentName?: string,
) {
  return function ErrorBoundaryWrapper(props: P) {
    return (
      <ErrorBoundary componentName={componentName || Component.name}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}

/**
 * Safe data access utilities - prevent crashes on missing data
 */
export const SafeData = {
  /**
   * Safely access nested properties without throwing
   */
  get<T = unknown>(obj: any, path: string, defaultValue?: T): T {
    try {
      const value = path.split('.').reduce((acc, part) => acc?.[part], obj);
      return value ?? defaultValue;
    } catch {
      return defaultValue as T;
    }
  },

  /**
   * Safely filter array of objects
   */
  filterValid<T>(items: any[], predicate: (item: any) => item is T): T[] {
    try {
      return items.filter(predicate);
    } catch {
      return [];
    }
  },

  /**
   * Safely map over array
   */
  map<T, R>(items: T[] | undefined, fn: (item: T) => R, defaultValue: R[] = []): R[] {
    try {
      return (items || []).map(fn);
    } catch {
      return defaultValue;
    }
  },
};
