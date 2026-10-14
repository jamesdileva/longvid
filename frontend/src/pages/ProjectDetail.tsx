import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import VideoCard from '../components/VideoCard';
import VideoImportForm from '../components/VideoImportForm';
import { getProject, updateProject } from '../services/projects';
import { deleteVideo, importVideo, listVideos } from '../services/videos';
import type { Project } from '../types/project';
import type { Video } from '../types/video';
import { formatTimestamp, pluralize } from '../utils/format';

export default function ProjectDetail() {
  const { id = '' } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadVideos() {
    try {
      setVideos(await listVideos(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load videos');
    }
  }

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [loadedProject, loadedVideos] = await Promise.all([getProject(id), listVideos(id)]);
        if (!active) return;
        setProject(loadedProject);
        setVideos(loadedVideos);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [id]);

  async function handleImport(path: string) {
    setError(null);
    try {
      await importVideo(id, path);
      await loadVideos();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import video');
    }
  }

  async function handleDeleteVideo(videoId: number) {
    setError(null);
    try {
      await deleteVideo(videoId);
      await loadVideos();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete video');
    }
  }

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
          <dd>{pluralize(videos.length, 'video')}</dd>
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
        <VideoImportForm onImport={handleImport} />
        {error && (
          <p className="error-note" role="alert">
            {error}
          </p>
        )}
        {videos.length === 0 ? (
          <p className="empty-note" data-testid="videos-empty">
            No videos imported yet. Supported formats: MP4, MOV, MKV, WebM, AVI.
          </p>
        ) : (
          <ul className="video-grid" data-testid="video-list">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} onDelete={handleDeleteVideo} />
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <h2>Clips</h2>
        <p className="empty-note">Highlight detection and clipping arrive in later phases.</p>
      </div>
    </section>
  );
}
