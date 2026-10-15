import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import CandidatesPanel from '../components/CandidatesPanel';
import VideoCard from '../components/VideoCard';
import VideoImportForm from '../components/VideoImportForm';
import { getProject, updateProject } from '../services/projects';
import { deleteVideo, importVideo, listVideos } from '../services/videos';
import { generateCandidates } from '../services/candidates';
import { listVideoJobs, processVideo } from '../services/jobs';import type { Project } from '../types/project';
import type { Video } from '../types/video';
import type { Job } from '../types/job';
import { isActiveJob } from '../types/job';
import { formatTimestamp, pluralize } from '../utils/format';

const JOB_POLL_INTERVAL_MS = 1500;

export default function ProjectDetail() {
  const { id = '' } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [jobsByVideo, setJobsByVideo] = useState<Record<number, Job[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const videoElements = useRef(new Map<number, HTMLVideoElement | null>());

  const registerVideoElement = (videoId: number, element: HTMLVideoElement | null) => {
    videoElements.current.set(videoId, element);
  };

  function seekVideo(videoId: number, seconds: number) {
    const element = videoElements.current.get(videoId);
    if (!element) return;
    element.currentTime = seconds;
    void element.play().catch(() => undefined);
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

  // Load jobs for the visible videos, then poll while any job is active.
  useEffect(() => {
    if (videos.length === 0) {
      setJobsByVideo({});
      return;
    }
    let active = true;
    async function loadJobs() {
      try {
        const entries = await Promise.all(
          videos.map(async (video) => [video.id, await listVideoJobs(video.id)] as const),
        );
        if (active) setJobsByVideo(Object.fromEntries(entries));
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load jobs');
      }
    }
    void loadJobs();
    return () => {
      active = false;
    };
  }, [videos]);

  const hasActiveJobs = Object.values(jobsByVideo).some((jobs) => jobs.some(isActiveJob));

  // When jobs settle, reload videos so generated state (e.g. audio_path) appears.
  const hadActiveJobs = useRef(false);
  useEffect(() => {
    if (hasActiveJobs) {
      hadActiveJobs.current = true;
      return;
    }
    if (!hadActiveJobs.current) return;
    hadActiveJobs.current = false;
    let active = true;
    void listVideos(id).then((fresh) => {
      if (active) setVideos(fresh);
    });
    return () => {
      active = false;
    };
  }, [hasActiveJobs, id]);

  useEffect(() => {
    if (!hasActiveJobs) return;
    const timer = setInterval(() => {
      void Promise.all(
        videos.map(async (video) => [video.id, await listVideoJobs(video.id)] as const),
      ).then((entries) => setJobsByVideo(Object.fromEntries(entries)));
    }, JOB_POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [hasActiveJobs, videos]);

  async function handleImport(path: string) {
    setError(null);
    try {
      await importVideo(id, path);
      setVideos(await listVideos(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import video');
    }
  }

  async function handleExtractAudio(video: Video) {
    setError(null);
    try {
      await processVideo(video.id, 'extract_audio');
      const jobs = await listVideoJobs(video.id);
      setJobsByVideo((current) => ({ ...current, [video.id]: jobs }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start extraction');
    }
  }

  async function handleTranscribe(video: Video) {
    setError(null);
    try {
      await processVideo(video.id, 'transcribe');
      const jobs = await listVideoJobs(video.id);
      setJobsByVideo((current) => ({ ...current, [video.id]: jobs }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start transcription');
    }
  }

  async function handleAnalyze(video: Video) {
    setError(null);
    try {
      await processVideo(video.id, 'analyze_events');
      const jobs = await listVideoJobs(video.id);
      setJobsByVideo((current) => ({ ...current, [video.id]: jobs }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
    }
  }

  async function handleGenerateCandidates(video: Video) {
    setError(null);
    try {
      await generateCandidates(video.id);
      const jobs = await listVideoJobs(video.id);
      setJobsByVideo((current) => ({ ...current, [video.id]: jobs }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start candidate generation');
    }
  }

  async function handleDeleteVideo(videoId: number) {
    setError(null);
    try {
      await deleteVideo(videoId);
      setVideos(await listVideos(id));
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
              <VideoCard
                key={video.id}
                video={video}
                jobs={jobsByVideo[video.id] ?? []}
                onExtractAudio={handleExtractAudio}
                onTranscribe={handleTranscribe}
                onAnalyze={handleAnalyze}
                onGenerateCandidates={handleGenerateCandidates}
                onDelete={handleDeleteVideo}
                registerElement={(element) => registerVideoElement(video.id, element)}
              />
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <h2>Clips</h2>
        <CandidatesPanel
          projectId={id}
          videos={videos.map((video) => ({ id: video.id, filename: video.filename }))}
          onSeekVideo={seekVideo}
        />
      </div>
    </section>
  );
}
