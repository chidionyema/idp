import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Button,
  CircularProgress,
  Alert,
  Box,
  Stack,
  Typography,
  Chip,
} from '@material-ui/core';
import GetAppIcon from '@material-ui/icons/GetApp';

interface DagNode {
  id: string;
  kind: string;
  name: string;
  source?: string;
}

interface DagEdge {
  source: string;
  target: string;
}

interface DagData {
  schema: string;
  layer: string;
  nodes: DagNode[];
  edges: DagEdge[];
  content_hash?: string;
}

interface DriftReport {
  intent_nodes: number;
  reality_nodes: number;
  missing_nodes: string[];
  verdict: string;
  timestamp?: string;
}

const SovereignViewer: React.FC = () => {
  const [dag, setDag] = useState<DagData | null>(null);
  const [drift, setDrift] = useState<DriftReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [dagRes, driftRes] = await Promise.all([
        fetch('/api/sovereign/intent.dag.json'),
        fetch('/api/sovereign/drift-report.json'),
      ]);

      if (!dagRes.ok || !driftRes.ok) {
        throw new Error(
          `Failed to fetch: DAG ${dagRes.status}, Drift ${driftRes.status}`,
        );
      }

      const dagData = await dagRes.json();
      const driftData = await driftRes.json();

      setDag(dagData);
      setDrift(driftData);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const downloadFile = async (endpoint: string, filename: string) => {
    try {
      const res = await fetch(`/api/sovereign/${endpoint}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Download failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <Card>
      <CardHeader
        title="🏗️ Infrastructure Topology (Sovereign)"
        subheader={`Last refreshed: ${lastRefresh.toLocaleTimeString()}`}
      />
      <CardContent>
        <Stack spacing={3}>
          {loading && <CircularProgress />}

          {error && <Alert severity="error">{error}</Alert>}

          {dag && !loading && (
            <>
              {/* DAG Summary */}
              <Box>
                <Typography variant="h6">Topology Summary</Typography>
                <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                  <Chip label={`${dag.nodes.length} Nodes`} color="primary" />
                  <Chip label={`${dag.edges.length} Edges`} color="primary" />
                  <Chip label={`Layer: ${dag.layer}`} variant="outlined" />
                </Stack>
              </Box>

              {/* Content Integrity */}
              {dag.content_hash && (
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Content Hash (SHA-256):
                  </Typography>
                  <Typography
                    variant="code"
                    sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                      wordBreak: 'break-all',
                    }}
                  >
                    {dag.content_hash}
                  </Typography>
                </Box>
              )}

              {/* Export Buttons */}
              <Box>
                <Typography variant="h6">Export Formats</Typography>
                <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: 'wrap' }}>
                  <Button
                    variant="contained"
                    startIcon={<GetAppIcon />}
                    onClick={() => downloadFile('intent.dag.json', 'intent.dag.json')}
                  >
                    📥 JSON
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<GetAppIcon />}
                    onClick={() => downloadFile('intent.dag.dot', 'intent.dag.dot')}
                  >
                    📥 GraphViz
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<GetAppIcon />}
                    onClick={() => downloadFile('drift-report.json', 'drift-report.json')}
                  >
                    📥 Drift Report
                  </Button>
                </Stack>
              </Box>

              {/* Drift Status */}
              {drift && (
                <Box
                  sx={{
                    p: 2,
                    bgcolor:
                      drift.verdict === 'PASS' ? '#e8f5e9' : '#ffebee',
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="h6">
                    Drift Status:{' '}
                    <strong
                      style={{
                        color: drift.verdict === 'PASS' ? '#2e7d32' : '#c62828',
                      }}
                    >
                      {drift.verdict}
                    </strong>
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Intent: {drift.intent_nodes} nodes | Reality: {drift.reality_nodes}{' '}
                    nodes
                  </Typography>
                  {drift.missing_nodes && drift.missing_nodes.length > 0 && (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Missing: {drift.missing_nodes.join(', ')}
                    </Typography>
                  )}
                </Box>
              )}

              {/* Metrics by Source */}
              <Box>
                <Typography variant="body2" color="textSecondary">
                  Sources:
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  {Object.entries(
                    dag.nodes.reduce(
                      (acc, node) => {
                        const src = node.source || 'unknown';
                        acc[src] = (acc[src] || 0) + 1;
                        return acc;
                      },
                      {} as Record<string, number>,
                    ),
                  ).map(([source, count]) => (
                    <Chip key={source} label={`${source}: ${count}`} size="small" />
                  ))}
                </Stack>
              </Box>
            </>
          )}

          <Button
            variant="outlined"
            onClick={fetchData}
            disabled={loading}
            sx={{ mt: 2 }}
          >
            🔄 Refresh Now
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default SovereignViewer;
