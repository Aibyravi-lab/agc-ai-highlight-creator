"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getProjects,
  getThumbnailUrl,
  getReelUrl,
  downloadReel,
  downloadThumbnail,
  deleteProject,
} from "../services/api";
import type { ProjectItem } from "../types/pipeline";

export function ProjectsPanel() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await getProjects();
      setProjects(res.data || []);
    } catch {
      // silently fail — auth may not yet be ready on first mount
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  if (loading || projects.length === 0) return null;

  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
        My Projects
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} onDelete={refresh} />
        ))}
      </div>
    </div>
  );
}

function ProjectCard({ project, onDelete }: { project: ProjectItem; onDelete: () => void }) {
  const [deleting, setDeleting] = useState(false);

  const thumbnailUrl = getThumbnailUrl(
    project.thumbnail_path ?? undefined
  );
  const reelUrl = getReelUrl(
    project.horizontal_reel_path ?? undefined
  );
  const hasReel = Boolean(project.horizontal_reel_path);
  const hasThumbnail = Boolean(project.thumbnail_path);

  const formattedDate = project.created_at
    ? new Date(
        project.created_at.replace(" ", "T") + "Z"
      ).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";

  const handleOpen = () => {
    if (reelUrl) window.open(reelUrl, "_blank");
  };

  const handleDownloadReel = () => {
    downloadReel(project.horizontal_reel_path ?? undefined);
  };

  const handleDownloadThumbnail = () => {
    downloadThumbnail(project.thumbnail_path ?? undefined);
  };

  const handleDelete = async () => {
    if (
      !window.confirm(
        `Delete "${project.original_video_name}"?\n\nThis will permanently remove the project and all its assets.`
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await deleteProject(project.id);
      onDelete();
    } catch {
      setDeleting(false);
    }
  };

  return (
    <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden flex flex-col">
      {/* Thumbnail */}
      <div className="aspect-video bg-[#0a0b10] flex items-center justify-center relative">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={project.original_video_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-600">
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M15 10l4.553-2.069A1 1 0 0121 8.882v6.236a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
              />
            </svg>
            <span className="text-xs">No thumbnail</span>
          </div>
        )}
      </div>

      {/* Info + Actions */}
      <div className="p-4 flex flex-col gap-3 flex-1">
        <div>
          <p
            className="text-white text-sm font-medium truncate"
            title={project.original_video_name}
          >
            {project.original_video_name}
          </p>
          <p className="text-gray-500 text-xs mt-1">{formattedDate}</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap mt-auto pt-1">
          <button
            onClick={handleOpen}
            disabled={!hasReel}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:bg-[#1e2030] disabled:text-gray-600 disabled:cursor-not-allowed text-white transition-colors"
          >
            Open
          </button>
          <button
            onClick={handleDownloadReel}
            disabled={!hasReel}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1e2030] hover:bg-[#252840] disabled:opacity-40 disabled:cursor-not-allowed text-gray-300 transition-colors"
          >
            Download Reel
          </button>
          <button
            onClick={handleDownloadThumbnail}
            disabled={!hasThumbnail}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1e2030] hover:bg-[#252840] disabled:opacity-40 disabled:cursor-not-allowed text-gray-300 transition-colors"
          >
            Download Thumbnail
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600/20 hover:bg-red-600/40 disabled:opacity-40 disabled:cursor-not-allowed text-red-400 transition-colors ml-auto"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
