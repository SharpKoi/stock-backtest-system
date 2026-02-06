import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { api } from "../services/api";

interface StrategyFile {
  filename: string;
}

interface StrategyContent {
  filename: string;
  content: string;
}

function StrategyEditorPage() {
  const [files, setFiles] = useState<StrategyFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState("");
  const [showNewFileInput, setShowNewFileInput] = useState(false);

  useEffect(() => {
    loadFileList();
  }, []);

  const loadFileList = async () => {
    try {
      setLoading(true);
      const response = await api.get<StrategyFile[]>("/strategies/files");
      setFiles(response.data);
      setError(null);
    } catch (err) {
      setError("Failed to load strategy files");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadFile = async (filename: string) => {
    try {
      setLoading(true);
      const response = await api.get<StrategyContent>(`/strategies/files/${filename}`);
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
      await api.put(`/strategies/files/${selectedFile}`, {
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

    const defaultContent = `from vici_trade_sdk import Strategy, Portfolio
import pandas as pd


class ${newFileName.replace(/[^a-zA-Z0-9]/g, "")}(Strategy):
    """Custom trading strategy."""

    @property
    def name(self) -> str:
        return "${newFileName.replace(/[^a-zA-Z0-9 ]/g, "")}"

    def indicators(self) -> list[dict]:
        """Return indicator configurations to pre-compute."""
        return []

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        """Trading logic executed on each bar."""
        pass
`;

    try {
      setLoading(true);
      await api.post("/strategies/files", {
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
      await api.delete(`/strategies/files/${filename}`);
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

  const hasUnsavedChanges = content !== originalContent;

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      <div style={{ padding: "1rem", borderBottom: "1px solid #ccc" }}>
        <h1>Strategy Editor</h1>
        <p style={{ color: "#666", fontSize: "0.9rem" }}>
          Edit your trading strategies using the vici-trade-sdk
        </p>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* File List Sidebar */}
        <div
          style={{
            width: "250px",
            borderRight: "1px solid #ccc",
            padding: "1rem",
            overflowY: "auto",
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
              + New Strategy
            </button>
          </div>

          {showNewFileInput && (
            <div style={{ marginBottom: "1rem" }}>
              <input
                type="text"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                placeholder="strategy_name.py"
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
            <p style={{ color: "#666", fontSize: "0.8rem" }}>No strategy files found</p>
          )}
          {files.map((file) => (
            <div
              key={file.filename}
              style={{
                marginBottom: "0.5rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <button
                onClick={() => loadFile(file.filename)}
                style={{
                  flex: 1,
                  padding: "0.5rem",
                  textAlign: "left",
                  backgroundColor:
                    selectedFile === file.filename ? "#e7f3ff" : "white",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                }}
                disabled={loading}
              >
                {file.filename}
              </button>
              <button
                onClick={() => deleteFile(file.filename)}
                style={{
                  padding: "0.3rem 0.6rem",
                  backgroundColor: "#dc3545",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
                disabled={loading}
                title="Delete file"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Editor Area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Toolbar */}
          <div
            style={{
              padding: "0.5rem 1rem",
              borderBottom: "1px solid #ccc",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              backgroundColor: "#f8f9fa",
            }}
          >
            <div>
              {selectedFile ? (
                <span style={{ fontWeight: "bold" }}>
                  {selectedFile}
                  {hasUnsavedChanges && (
                    <span style={{ color: "#dc3545" }}> (unsaved)</span>
                  )}
                </span>
              ) : (
                <span style={{ color: "#666" }}>No file selected</span>
              )}
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
          <div style={{ flex: 1 }}>
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
                Select a file to edit or create a new strategy
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default StrategyEditorPage;
