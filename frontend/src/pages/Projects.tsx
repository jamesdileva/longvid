import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createProject, deleteProject, listProjects } from '../services/projects';
import type { Project } from '../types/project';
import { formatTimestamp, pluralize } from '../utils/format';

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setProjects(await listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setError(null);
    try {
      const project = await createProject({ name: trimmed, description: description.trim() || null });
      setProjects((current) => [project, ...current]);
      setName('');
      setDescription('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    }
  }

  async function handleDelete(id: string) {
    setError(null);
    try {
      await deleteProject(id);
      setProjects((current) => current.filter((project) => project.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    } finally {
      setConfirmingId(null);
    }
  }

  return (
    <section>
      <h1>Projects</h1>

      <div className="panel">
        <h2>New project</h2>
        <form className="project-form" onSubmit={handleCreate}>
          <input
            aria-label="Project name"
            placeholder="Project name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <input
            aria-label="Description (optional)"
            placeholder="Description (optional)"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <button type="submit" disabled={!name.trim()}>
            Create project
          </button>
        </form>
      </div>

      {error && (
        <p className="error-note" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="empty-note">Loading projects…</p>
      ) : projects.length === 0 ? (
        <p className="empty-note" data-testid="projects-empty">
          No projects yet. Create one above to get started.
        </p>
      ) : (
        <ul className="project-grid" data-testid="project-list">
          {projects.map((project) => (
            <li className="card" key={project.id} data-testid="project-card">
              <div className="card-header">
                <Link to={`/projects/${project.id}`}>{project.name}</Link>
                <span className={`status-pill ${project.status}`}>{project.status}</span>
              </div>
              {project.description && <p className="card-description">{project.description}</p>}
              <dl className="card-stats">
                <dt>Videos</dt>
                <dd data-testid="video-count">{pluralize(project.video_count, 'video')}</dd>
                <dt>Clips</dt>
                <dd data-testid="clip-count">{pluralize(project.clip_count, 'clip')}</dd>
                <dt>Last modified</dt>
                <dd data-testid="last-modified">{formatTimestamp(project.updated_at)}</dd>
                <dt>Processing</dt>
                <dd>Idle</dd>
              </dl>
              {confirmingId === project.id ? (
                <div className="card-actions">
                  <button
                    type="button"
                    className="danger"
                    onClick={() => void handleDelete(project.id)}
                  >
                    Confirm delete
                  </button>
                  <button type="button" onClick={() => setConfirmingId(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="card-actions">
                  <button type="button" onClick={() => setConfirmingId(project.id)}>
                    Delete
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
