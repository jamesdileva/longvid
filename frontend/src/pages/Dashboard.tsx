import { useEffect, useState } from 'react';
import { fetchHealth } from '../services/api';
import type { HealthResponse } from '../types/health';

const PIPELINE_STAGES = [
  'Import Video',
  'Media Inspection',
  'Audio / Video Processing',
  'Transcription',
  'Scene / Event Detection',
  'Moment Segmentation',
  'Candidate Scoring',
  'Clip Generation',
  'Automated Editing',
  'Preview / Review',
  'Export',
];

type Status = 'checking' | 'online' | 'offline';

export default function Dashboard() {
  const [status, setStatus] = useState<Status>('checking');
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let active = true;
    fetchHealth()
      .then((result) => {
        if (active) {
          setHealth(result);
          setStatus(result.status === 'ok' ? 'online' : 'offline');
        }
      })
      .catch(() => {
        if (active) setStatus('offline');
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h1>Dashboard</h1>
      <div className="panel">
        <h2>Backend status</h2>
        <p>
          <span className={`status-pill ${status}`} data-testid="backend-status">
            {status === 'checking' ? 'Checking…' : status === 'online' ? 'Online' : 'Offline'}
          </span>
        </p>
        {health && (
          <dl className="health-details">
            <dt>Version</dt>
            <dd data-testid="backend-version">{health.version}</dd>
            <dt>Database</dt>
            <dd>{health.database}</dd>
          </dl>
        )}
      </div>
      <div className="panel">
        <h2>Pipeline</h2>
        <ol className="pipeline-list">
          {PIPELINE_STAGES.map((stage) => (
            <li key={stage}>{stage}</li>
          ))}
        </ol>
      </div>
    </section>
  );
}
