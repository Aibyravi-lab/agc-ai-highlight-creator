"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getProjects,
  downloadReel,
  downloadThumbnail,
  deleteProject,
} from "../services/api";
import { track } from "../services/analytics";
import { useAuthedMediaUrl } from "../hooks/useAuthedMediaUrl";
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

  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
        My Projects
      </h2>

      {loading ? (
        <div className="flex items-center justify-center py-10">
          <div
            className="w-5 h-5 rounded-full border-2 border-green-500 border-t-transparent animate-spin"
            aria-label="Loading projects"
          />
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border border-[#1e2030] bg-[#0f1117] p-10 text-center">
          <svg
            className="w-10 h-10 mx-auto mb-3 text-gray-700"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <p className="text-gray-500 text-sm">Your generated projects will appear here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} onDelete={refresh} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project, onDelete }: { project: ProjectItem; onDelete: () => void }) {
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState(false);

  const thumbnailUrl = useAuthedMediaUrl(project.thumbnail_path);
  const reelUrl = useAuthedMediaUrl(project.horizontal_reel_path);
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
    track("Project Downloaded");
    downloadReel(project.horizontal_reel_path ?? undefined);
  };

  const handleDownloadThumbnail = () => {
    track("Project Downloaded");
    downloadThumbnail(project.thumbnail_path ?? undefined);
  };

  const handleDeleteClick = () => {
    setDeleteError(null);
    setConfirmDelete(true);
  };

  const handleCancelDelete = () => {
    setConfirmDelete(false);
  };

  const handleConfirmDelete = async () => {
    setConfirmDelete(false);
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteProject(project.id);
      track("Project Deleted");
      setDeleteSuccess(true);
      setTimeout(() => onDelete(), 1200);
    } catch {
      setDeleting(false);
      setDeleteError("Failed to delete. Please try again.");
    }
  };

  return (
    <div
      className={`rounded-xl border border-[#1e2030] bg-[#0f1117] overflow-hidden flex flex-col transition-opacity duration-300 ${
        deleteSuccess ? "opacity-40 pointer-events-none" : ""
      }`}
    >
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
              aria-hidden="true"
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

        {/* Status messages */}
        {deleteSuccess && (
          <p className="text-green-400 text-xs font-medium">Project deleted successfully.</p>
        )}
        {deleteError && (
          <p className="text-red-400 text-xs">{deleteError}</p>
        )}

        {/* Inline delete confirmation */}
        {confirmDelete ? (
          <div className="mt-auto pt-1 space-y-2">
            <p className="text-xs text-gray-400">
              Permanently delete this project and all its assets?
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleConfirmDelete}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 hover:bg-red-700 text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500"
              >
                Delete
              </button>
              <button
                onClick={handleCancelDelete}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1e2030] hover:bg-[#252840] text-gray-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-500"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 flex-wrap mt-auto pt-1">
            <button
              onClick={handleOpen}
              disabled={!hasReel}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:bg-[#1e2030] disabled:text-gray-600 disabled:cursor-not-allowed text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
            >
              Open
            </button>
            <button
              onClick={handleDownloadReel}
              disabled={!hasReel}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1e2030] hover:bg-[#252840] disabled:opacity-40 disabled:cursor-not-allowed text-gray-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-500"
            >
              Download Reel
            </button>
            <button
              onClick={handleDownloadThumbnail}
              disabled={!hasThumbnail}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1e2030] hover:bg-[#252840] disabled:opacity-40 disabled:cursor-not-allowed text-gray-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-gray-500"
            >
              Download Thumbnail
            </button>
            <button
              onClick={handleDeleteClick}
              disabled={deleting}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600/20 hover:bg-red-600/40 disabled:opacity-40 disabled:cursor-not-allowed text-red-400 transition-colors ml-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500"
              aria-label={`Delete project ${project.original_video_name}`}
            >
              {deleting ? "Deleting…" : "Delete"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
