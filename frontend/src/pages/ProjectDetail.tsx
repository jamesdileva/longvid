import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getProject, updateProject } from '../services/projects';
import type { Project } from '../types/project';
import { formatTimestamp, pluralize } from '../utils/format';

export default function ProjectDetail() {
  const { id = '' } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setProject(await getProject(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only on id change
  }, [id]);

  async function toggleStatus() {
    if (!project) return;
    const next = project.status === 'active' ? 'archived' : 'active';
    try {
      setProject(await updateProject(project.id, { status: next }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update project');
    }
  }

  if (loading) return <p className="empty-note">Loading project…</p>;
  if (error || !project) {
    return (
      <section>
        <p className="error-note" role="alert">
          {error ?? 'Project not found'}
        </p>
        <Link to="/projects">Back to projects</Link>
      </section>
    );
  }

  return (
    <section>
      <p>
        <Link to="/projects">← All projects</Link>
      </p>
      <h1>{project.name}</h1>
      <div className="panel">
        <h2>Overview</h2>
        <dl className="detail-grid">
          <dt>Status</dt>
          <dd data-testid="project-status">{project.status}</dd>
          <dt>Description</dt>
          <dd>{project.description ?? '—'}</dd>
          <dt>Videos</dt>
          <dd>{pluralize(project.video_count, 'video')}</dd>
          <dt>Clips</dt>
          <dd>{pluralize(project.clip_count, 'clip')}</dd>
          <dt>Workspace</dt>
          <dd>
            <code>{project.workspace_path}</code>
          </dd>
          <dt>Created</dt>
          <dd>{formatTimestamp(project.created_at)}</dd>
          <dt>Updated</dt>
          <dd>{formatTimestamp(project.updated_at)}</dd>
        </dl>
        <div className="card-actions">
          <button type="button" onClick={() => void toggleStatus()}>
            {project.status === 'active' ? 'Archive' : 'Reactivate'}
          </button>
        </div>
      </div>
      <div className="panel">
        <h2>Videos</h2>
        <p className="empty-note">Video import arrives in Sprint 3.</p>
      </div>
      <div className="panel">
        <h2>Clips</h2>
        <p className="empty-note">Highlight detection and clipping arrive in later phases.</p>
      </div>
    </section>
  );
}
