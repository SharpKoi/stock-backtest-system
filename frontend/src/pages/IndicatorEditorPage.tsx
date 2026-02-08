import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { Trash2, Menu, X } from "lucide-react";
import { api } from "../services/api";

interface IndicatorFile {
  filename: string;
}

interface IndicatorContent {
  filename: string;
  content: string;
}

interface FileItemState {
  isHovered: boolean;
  deleteHovered: boolean;
}

function IndicatorEditorPage() {
  const [files, setFiles] = useState<IndicatorFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState("");
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  const [fileHoverStates, setFileHoverStates] = useState<Record<string, FileItemState>>({});
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [sidebarVisible, setSidebarVisible] = useState(true);

  useEffect(() => {
    loadFileList();
  }, []);

  useEffect(() => {
    // Auto-hide sidebar on small screens
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarVisible(false);
      } else {
        setSidebarVisible(true);
      }
    };

    // Initial check
    handleResize();

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const loadFileList = async () => {
    try {
      setLoading(true);
      const response = await api.get<IndicatorFile[]>("/indicators/files");
      setFiles(response.data);
      setError(null);
    } catch (err) {
      setError("Failed to load indicator files");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadFile = async (filename: string) => {
    try {
      setLoading(true);
      const response = await api.get<IndicatorContent>(`/indicators/files/${filename}`);
      setContent(response.data.content);
      setOriginalContent(response.data.content);
      setSelectedFile(filename);
      setError(null);
      setMessage(null);
    } catch (err) {
      setError(`Failed to load file: ${filename}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveFile = async () => {
    if (!selectedFile) return;

    try {
      setLoading(true);
      await api.put(`/indicators/files/${selectedFile}`, {
        filename: selectedFile,
        content: content,
      });
      setOriginalContent(content);
      setMessage(`Saved ${selectedFile} successfully`);
      setError(null);
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setError(`Failed to save file: ${selectedFile}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const createNewFile = async () => {
    if (!newFileName.trim()) {
      setError("Please enter a filename");
      return;
    }

    const filename = newFileName.endsWith(".py") ? newFileName : `${newFileName}.py`;

    const defaultContent = `from vici_trade_sdk import Indicator
import pandas as pd
import numpy as np


class ${newFileName.replace(/[^a-zA-Z0-9]/g, "")}(Indicator):
    """Custom technical indicator."""

    @property
    def name(self) -> str:
        return "${newFileName.replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase()}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute indicator from OHLCV data.

        Args:
            df: DataFrame with columns: open, high, low, close, volume

        Returns:
            Series with indicator values
        """
        # Your computation logic here
        return df["close"].rolling(window=20).mean()
`;

    try {
      setLoading(true);
      await api.post("/indicators/files", {
        filename: filename,
        content: defaultContent,
      });
      setMessage(`Created ${filename} successfully`);
      setError(null);
      setNewFileName("");
      setShowNewFileInput(false);
      await loadFileList();
      await loadFile(filename);
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setError(`Failed to create file: ${filename}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
      return;
    }

    try {
      setLoading(true);
      await api.delete(`/indicators/files/${filename}`);
      setMessage(`Deleted ${filename} successfully`);
      setError(null);
      if (selectedFile === filename) {
        setSelectedFile(null);
        setContent("");
        setOriginalContent("");
      }
      await loadFileList();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setError(`Failed to delete file: ${filename}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const startRename = (filename: string) => {
    setEditingFile(filename);
    setEditingName(filename);
  };

  const cancelRename = () => {
    setEditingFile(null);
    setEditingName("");
  };

  const renameFile = async (oldFilename: string, newFilename: string) => {
    // Validation
    if (!newFilename.trim()) {
      setError("Filename cannot be empty");
      return;
    }

    if (!newFilename.endsWith(".py")) {
      setError("Filename must end with .py");
      return;
    }

    if (newFilename === oldFilename) {
      cancelRename();
      return;
    }

    // Check for duplicates
    if (files.some((f) => f.filename === newFilename)) {
      setError(`File ${newFilename} already exists`);
      return;
    }

    // Validate characters (no path traversal)
    if (newFilename.includes("..") || newFilename.includes("/") || newFilename.includes("\\")) {
      setError("Invalid filename: cannot contain path traversal characters");
      return;
    }

    try {
      setLoading(true);
      await api.post(`/indicators/files/${oldFilename}/rename`, {
        new_filename: newFilename,
      });
      setMessage(`Renamed ${oldFilename} to ${newFilename} successfully`);
      setError(null);

      // Update selected file if it was the renamed one
      if (selectedFile === oldFilename) {
        setSelectedFile(newFilename);
      }

      cancelRename();
      await loadFileList();
      setTimeout(() => setMessage(null), 3000);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || `Failed to rename file: ${oldFilename}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const hasUnsavedChanges = content !== originalContent;

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: "1rem", borderBottom: "1px solid #ccc", flexShrink: 0 }}>
        <h1>Indicator Editor</h1>
        <p style={{ color: "#666", fontSize: "0.9rem" }}>
          Create custom technical indicators using the vici-trade-sdk
        </p>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>
        {/* File List Sidebar */}
        <div
          style={{
            width: sidebarVisible ? "250px" : "0",
            minWidth: sidebarVisible ? "250px" : "0",
            maxWidth: sidebarVisible ? "250px" : "0",
            borderRight: sidebarVisible ? "1px solid #ccc" : "none",
            padding: sidebarVisible ? "1rem" : "0",
            overflowY: "auto",
            overflowX: "hidden",
            transition: "all 0.3s ease",
            flexShrink: 0,
          }}
        >
          <div style={{ marginBottom: "1rem" }}>
            <button
              onClick={() => setShowNewFileInput(!showNewFileInput)}
              style={{
                width: "100%",
                padding: "0.5rem",
                backgroundColor: "#007bff",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
              disabled={loading}
            >
              + New Indicator
            </button>
          </div>

          {showNewFileInput && (
            <div style={{ marginBottom: "1rem" }}>
              <input
                type="text"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                placeholder="indicator_name.py"
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  marginBottom: "0.5rem",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                }}
              />
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  onClick={createNewFile}
                  style={{
                    flex: 1,
                    padding: "0.5rem",
                    backgroundColor: "#28a745",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                  disabled={loading}
                >
                  Create
                </button>
                <button
                  onClick={() => {
                    setShowNewFileInput(false);
                    setNewFileName("");
                  }}
                  style={{
                    flex: 1,
                    padding: "0.5rem",
                    backgroundColor: "#6c757d",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <h3 style={{ fontSize: "0.9rem", marginBottom: "0.5rem" }}>Files</h3>
          {files.length === 0 && !loading && (
            <p style={{ color: "#666", fontSize: "0.8rem" }}>No indicator files found</p>
          )}
          {files.map((file) => {
            const hoverState = fileHoverStates[file.filename] || { isHovered: false, deleteHovered: false };
            const isEditing = editingFile === file.filename;

            return (
              <div
                key={file.filename}
                onMouseEnter={() =>
                  setFileHoverStates((prev) => ({
                    ...prev,
                    [file.filename]: { ...prev[file.filename], isHovered: true },
                  }))
                }
                onMouseLeave={() =>
                  setFileHoverStates((prev) => ({
                    ...prev,
                    [file.filename]: { isHovered: false, deleteHovered: false },
                  }))
                }
                style={{
                  marginBottom: "0.25rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.5rem 0.75rem",
                  borderRadius: "4px",
                  cursor: isEditing ? "default" : "pointer",
                  backgroundColor:
                    selectedFile === file.filename
                      ? "#303842"
                      : hoverState.isHovered
                      ? "#303842"
                      : "transparent",
                  transition: "background-color 0.15s ease",
                }}
              >
                {isEditing ? (
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        renameFile(file.filename, editingName);
                      } else if (e.key === "Escape") {
                        cancelRename();
                      }
                    }}
                    onBlur={() => cancelRename()}
                    autoFocus
                    style={{
                      flex: 1,
                      fontSize: "0.875rem",
                      padding: "0.25rem 0.5rem",
                      border: "1px solid #3b82f6",
                      borderRadius: "3px",
                      outline: "none",
                    }}
                  />
                ) : (
                  <>
                    <span
                      onDoubleClick={(e) => {
                        e.stopPropagation();
                        startRename(file.filename);
                      }}
                      onClick={() => loadFile(file.filename)}
                      style={{
                        flex: 1,
                        fontSize: "0.875rem",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {file.filename}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteFile(file.filename);
                      }}
                      onMouseEnter={() =>
                        setFileHoverStates((prev) => ({
                          ...prev,
                          [file.filename]: { ...prev[file.filename], deleteHovered: true },
                        }))
                      }
                      onMouseLeave={() =>
                        setFileHoverStates((prev) => ({
                          ...prev,
                          [file.filename]: { ...prev[file.filename], deleteHovered: false },
                        }))
                      }
                      style={{
                        marginLeft: "0.5rem",
                        padding: "0.25rem",
                        backgroundColor: "transparent",
                        border: "none",
                        cursor: "pointer",
                        color: hoverState.deleteHovered ? "#ef4444" : "#9ca3af",
                        transition: "color 0.15s ease",
                      }}
                      disabled={loading}
                      title="Delete file"
                    >
                      <Trash2 size={16} />
                    </button>
                  </>
                )}
              </div>
            );
          })}
        </div>

        {/* Editor Area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
          {/* Toolbar */}
          <div
            style={{
              padding: "0.5rem 1rem",
              borderBottom: "1px solid #ccc",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              backgroundColor: "#f8f9fa",
              flexShrink: 0,
              gap: "0.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", minWidth: 0, flex: 1 }}>
              <button
                onClick={() => setSidebarVisible(!sidebarVisible)}
                style={{
                  padding: "0.5rem",
                  backgroundColor: "transparent",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#666",
                  flexShrink: 0,
                }}
                title={sidebarVisible ? "Hide sidebar" : "Show sidebar"}
              >
                {sidebarVisible ? <X size={18} /> : <Menu size={18} />}
              </button>
              <div style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {selectedFile ? (
                  <span
                    style={{
                      fontWeight: 600,
                      color: hasUnsavedChanges ? "#ea580c" : "#111827",
                    }}
                  >
                    {selectedFile}
                    {hasUnsavedChanges && "*"}
                  </span>
                ) : (
                  <span style={{ color: "#666" }}>No file selected</span>
                )}
              </div>
            </div>
            <button
              onClick={saveFile}
              disabled={!selectedFile || !hasUnsavedChanges || loading}
              style={{
                padding: "0.5rem 1rem",
                backgroundColor: hasUnsavedChanges ? "#28a745" : "#6c757d",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: hasUnsavedChanges ? "pointer" : "not-allowed",
                flexShrink: 0,
                whiteSpace: "nowrap",
              }}
            >
              {loading ? "Saving..." : "Save"}
            </button>
          </div>

          {/* Status Messages */}
          {error && (
            <div
              style={{
                padding: "0.75rem",
                backgroundColor: "#f8d7da",
                color: "#721c24",
                borderBottom: "1px solid #f5c6cb",
              }}
            >
              {error}
            </div>
          )}
          {message && (
            <div
              style={{
                padding: "0.75rem",
                backgroundColor: "#d4edda",
                color: "#155724",
                borderBottom: "1px solid #c3e6cb",
              }}
            >
              {message}
            </div>
          )}

          {/* Monaco Editor */}
          <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
            {selectedFile ? (
              <Editor
                height="100%"
                defaultLanguage="python"
                value={content}
                onChange={(value) => setContent(value || "")}
                theme="vs-dark"
                options={{
                  minimap: { enabled: true },
                  fontSize: 14,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  wordWrap: "on",
                }}
              />
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#666",
                }}
              >
                Select a file to edit or create a new indicator
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default IndicatorEditorPage;
