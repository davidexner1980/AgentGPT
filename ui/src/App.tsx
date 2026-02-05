import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import clsx from "clsx";
import { listen } from "@tauri-apps/api/event";
import {
  API_BASE,
  getAuditLogs,
  getConfig,
  getDreamLogs,
  getModels,
  getReflectionLogs,
  openChatStream,
  sendChat,
  updateConfig,
} from "./lib/api";

type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
  model?: string;
};

type ApprovalDetail = {
  allowed: boolean;
  reason: string;
  scope: string;
  requires_approval: boolean;
};

const defaultSessionId = crypto.randomUUID();

export default function App() {
  const [models, setModels] = useState<string[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [taskType, setTaskType] = useState<string>("qa");
  const [speedQuality, setSpeedQuality] = useState(50);
  const [useRag, setUseRag] = useState(true);
  const [isStreaming, setIsStreaming] = useState(true);
  const [activeTab, setActiveTab] = useState<"chat" | "settings" | "logs">("chat");
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [dreamLogs, setDreamLogs] = useState<any[]>([]);
  const [reflectionLogs, setReflectionLogs] = useState<any[]>([]);
  const [approvalDetail, setApprovalDetail] = useState<ApprovalDetail | null>(null);
  const [routerJson, setRouterJson] = useState("");
  const [status, setStatus] = useState<string>("Ready");
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandInput, setCommandInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState("");
  const [ingestPath, setIngestPath] = useState("");
  const [ingestStatus, setIngestStatus] = useState("");
  const [routerTestInput, setRouterTestInput] = useState("");
  const [routerTestResult, setRouterTestResult] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const assistantBufferRef = useRef("");

  useEffect(() => {
    async function load() {
      try {
        const modelResponse = await getModels();
        const names = modelResponse.models.map((model: any) => model.name);
        setModels(names);
        setSelectedModel(names[0] ?? "");
      } catch {
        setStatus("Failed to load models from Ollama");
      }
      try {
        const configResponse = await getConfig();
        setConfig(configResponse);
        setRouterJson(JSON.stringify(configResponse.routing, null, 2));
        setUseRag(configResponse.rag?.enabled ?? true);
      } catch {
        setStatus("Failed to load config");
      }
    }
    load();
  }, []);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let unlistenHandsFree: (() => void) | undefined;
    let unlistenMute: (() => void) | undefined;
    if ((window as any).__TAURI__) {
      listen("command_bar:open", () => setCommandOpen(true)).then((handler) => {
        unlisten = handler;
      });
      listen("hands_free:toggle", () => {
        toggleHandsFree();
      }).then((handler) => {
        unlistenHandsFree = handler;
      });
      listen("audio:mute", () => setTtsEnabled(false)).then((handler) => {
        unlistenMute = handler;
      });
    }
    return () => {
      if (unlisten) {
        unlisten();
      }
      if (unlistenHandsFree) {
        unlistenHandsFree();
      }
      if (unlistenMute) {
        unlistenMute();
      }
    };
  }, []);

  useEffect(() => {
    if (activeTab !== "logs") {
      return;
    }
    async function loadLogs() {
      const [audit, dreams, reflections] = await Promise.all([
        getAuditLogs(200),
        getDreamLogs(50),
        getReflectionLogs(50),
      ]);
      setAuditLogs(audit.entries ?? []);
      setDreamLogs(dreams.entries ?? []);
      setReflectionLogs(reflections.entries ?? []);
    }
    loadLogs();
  }, [activeTab]);

  const sessionId = useMemo(() => defaultSessionId, []);

  async function handleSend(textOverride?: string) {
    const text = textOverride ?? input;
    if (!text.trim()) {
      return;
    }
    setApprovalDetail(null);
    const userMessage: ChatMessage = { role: "user", content: text };
    const payload = {
      session_id: sessionId,
      messages: [...messages, userMessage],
      model: selectedModel || undefined,
      task_type: taskType,
      speed_quality: speedQuality,
      stream: isStreaming,
      use_rag: useRag,
    };
    setMessages((prev) => [...prev, userMessage, { role: "assistant", content: "" }]);
    setInput("");
    if (!isStreaming) {
      try {
        const response = await sendChat(payload);
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: response.content,
            model: response.model,
          };
          return updated;
        });
        await maybeSpeak(response.content);
      } catch (error) {
        handleError(error);
      }
      return;
    }
    assistantBufferRef.current = "";
    const socket = openChatStream(payload);
    socket.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "token") {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          assistantBufferRef.current = `${assistantBufferRef.current}${data.content}`;
          updated[updated.length - 1] = {
            ...last,
            content: `${last.content}${data.content}`,
          };
          return updated;
        });
      }
      if (data.type === "routing") {
        setStatus(`Model: ${data.model} (${data.rule ?? "auto"})`);
      }
      if (data.type === "done") {
        maybeSpeak(assistantBufferRef.current);
        assistantBufferRef.current = "";
      }
      if (data.type === "error") {
        setStatus(`Error: ${data.error}`);
      }
    });
    socket.addEventListener("close", () => {
      setStatus("Ready");
    });
  }

  async function maybeSpeak(text: string) {
    if (!ttsEnabled || !config?.voice?.enabled) {
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/voice/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        return;
      }
      const audioBlob = await response.blob();
      const url = URL.createObjectURL(audioBlob);
      const audio = new Audio(url);
      audio.play();
    } catch {
      setStatus("TTS failed");
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        setRecordingStatus("Transcribing...");
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", blob, "audio.webm");
        const response = await fetch(`${API_BASE}/voice/transcribe`, {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          setRecordingStatus("Transcription failed");
          return;
        }
        const data = await response.json();
        setRecordingStatus(`Transcript: ${data.text}`);
        await handleSend(data.text);
      };
      recorder.start();
      setIsRecording(true);
      setRecordingStatus("Recording...");
    } catch {
      setRecordingStatus("Microphone access denied");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    setIsRecording(false);
  }

  async function handleCommandSend() {
    if (!commandInput.trim()) {
      return;
    }
    setCommandOpen(false);
    await handleSend(commandInput);
    setCommandInput("");
  }

  function handleError(error: unknown) {
    if (error instanceof Error) {
      const detail = (error as Error & { detail?: unknown }).detail;
      if (detail && typeof detail === "object") {
        setApprovalDetail(detail as ApprovalDetail);
        setStatus("Approval required");
        return;
      }
      setStatus(error.message);
    }
  }

  async function handleSaveConfig() {
    if (!config) {
      return;
    }
    try {
      const routing = JSON.parse(routerJson);
      const updated = { ...config, routing };
      const response = await updateConfig(updated);
      setConfig(response);
      setStatus("Config saved");
    } catch (error) {
      setStatus("Invalid config JSON");
    }
  }

  async function handleApprove(scope: string, mode: "once" | "always") {
    if (!config) {
      return;
    }
    if (mode === "always") {
      const updated = { ...config };
      if (scope.startsWith("file_read:")) {
        updated.permissions.file_read_allowlist.push(scope.replace("file_read:", ""));
      } else if (scope.startsWith("file_write:")) {
        updated.permissions.file_write_allowlist.push(scope.replace("file_write:", ""));
      } else if (scope.startsWith("terminal:")) {
        updated.permissions.terminal_allowlist.push(scope.replace("terminal:", ""));
      } else if (scope.startsWith("skill:")) {
        updated.permissions.skills_enabled.push(scope.replace("skill:", ""));
      }
      const response = await updateConfig(updated);
      setConfig(response);
      setApprovalDetail(null);
      setStatus("Approval saved");
      return;
    }
    await fetch(`${API_BASE}/approvals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope,
        expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
      }),
    });
    setApprovalDetail(null);
    setStatus("Approved once");
  }

  async function toggleHandsFree() {
    if (!config) {
      return;
    }
    const updated = {
      ...config,
      voice: { ...config.voice, hands_free: !config.voice.hands_free },
    };
    const response = await updateConfig(updated);
    setConfig(response);
  }

  async function handleIngest() {
    if (!ingestPath.trim()) {
      return;
    }
    setIngestStatus("Ingesting...");
    const response = await fetch(`${API_BASE}/rag/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paths: [ingestPath] }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      setIngestStatus(`Failed: ${error.detail ?? "permission required"}`);
      return;
    }
    const data = await response.json();
    setIngestStatus(`Indexed: ${(data.indexed || []).length}`);
  }

  async function handleRouterTest() {
    if (!routerTestInput.trim()) {
      return;
    }
    setRouterTestResult("Testing...");
    const response = await fetch(`${API_BASE}/router/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: routerTestInput, speed_quality: speedQuality }),
    });
    if (!response.ok) {
      setRouterTestResult("Test failed");
      return;
    }
    const data = await response.json();
    setRouterTestResult(`Model: ${data.model} (rule: ${data.rule ?? "none"})`);
  }

  return (
    <div className="min-h-screen p-6">
      <header className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-semibold">Local AI Assistant</h1>
          <p className="text-sm text-slate-400">
            Local-only | Ollama | {API_BASE}
          </p>
        </div>
        <div className="flex gap-2">
          {(["chat", "settings", "logs"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                "rounded-full px-3 py-1 text-sm",
                activeTab === tab
                  ? "bg-indigo-500 text-white"
                  : "bg-slate-800 text-slate-200"
              )}
            >
              {tab}
            </button>
          ))}
        </div>
      </header>

      {activeTab === "chat" && (
        <div className="mt-6 grid gap-6 lg:grid-cols-[280px_1fr]">
          <aside className="rounded-2xl border border-slate-800 p-4">
            <h2 className="text-sm font-semibold text-slate-300">Session</h2>
            <div className="mt-3 text-xs text-slate-500">ID: {sessionId}</div>
            <div className="mt-6 space-y-3 text-sm">
              <label className="block">
                <span className="text-xs text-slate-400">Model</span>
                <select
                  className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-2"
                  value={selectedModel}
                  onChange={(event) => setSelectedModel(event.target.value)}
                >
                  {models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-xs text-slate-400">Task type</span>
                <select
                  className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-2"
                  value={taskType}
                  onChange={(event) => setTaskType(event.target.value)}
                >
                  <option value="qa">Quick Q&A</option>
                  <option value="coding">Coding</option>
                  <option value="reasoning">Reasoning</option>
                  <option value="voice">Voice</option>
                </select>
              </label>
              <label className="block">
                <span className="text-xs text-slate-400">
                  Speed vs Quality: {speedQuality}
                </span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={speedQuality}
                  onChange={(event) => setSpeedQuality(Number(event.target.value))}
                  className="mt-2 w-full"
                />
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={useRag}
                  onChange={(event) => setUseRag(event.target.checked)}
                />
                Use RAG
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={isStreaming}
                  onChange={(event) => setIsStreaming(event.target.checked)}
                />
                Stream tokens
              </label>
            </div>
          </aside>

          <main className="rounded-2xl border border-slate-800 p-6">
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={clsx(
                    "rounded-xl p-4 text-sm",
                    message.role === "user"
                      ? "bg-slate-800 text-slate-100"
                      : "bg-slate-900 text-slate-200"
                  )}
                >
                  <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                    {message.role}
                  </div>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                  >
                    {message.content || "..."}
                  </ReactMarkdown>
                </div>
              ))}
            </div>
            <div className="mt-6 flex gap-2">
              <input
                className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm"
                placeholder="Ask locally..."
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    handleSend();
                  }
                }}
              />
              <button
                onClick={handleSend}
                className="rounded-lg bg-indigo-500 px-4 py-3 text-sm font-semibold text-white"
              >
                Send
              </button>
              <button
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onMouseLeave={() => {
                  if (isRecording) {
                    stopRecording();
                  }
                }}
                className={clsx(
                  "rounded-lg px-4 py-3 text-sm font-semibold",
                  isRecording ? "bg-rose-500 text-white" : "bg-slate-800 text-slate-200"
                )}
              >
                {isRecording ? "Recording..." : "Push to Talk"}
              </button>
            </div>
            {recordingStatus && (
              <div className="mt-2 text-xs text-slate-500">{recordingStatus}</div>
            )}
            {approvalDetail && (
              <div className="mt-6 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm">
                <p className="font-semibold text-amber-200">Needs approval</p>
                <p className="text-amber-100">{approvalDetail.reason}</p>
                <p className="mt-1 text-xs text-amber-200">
                  Scope: {approvalDetail.scope}
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleApprove(approvalDetail.scope, "once")}
                    className="rounded-md bg-amber-400 px-3 py-1 text-xs font-semibold text-slate-900"
                  >
                    Approve once
                  </button>
                  <button
                    onClick={() => handleApprove(approvalDetail.scope, "always")}
                    className="rounded-md bg-amber-200 px-3 py-1 text-xs font-semibold text-slate-900"
                  >
                    Approve always
                  </button>
                </div>
              </div>
            )}
            <div className="mt-4 text-xs text-slate-500">{status}</div>
          </main>
        </div>
      )}

      {commandOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/80 pt-24">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-xl">
            <div className="text-xs text-slate-400">Command Bar</div>
            <input
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              placeholder="Ask quickly..."
              value={commandInput}
              onChange={(event) => setCommandInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleCommandSend();
                }
                if (event.key === "Escape") {
                  setCommandOpen(false);
                }
              }}
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => setCommandOpen(false)}
                className="rounded-md bg-slate-800 px-3 py-1 text-xs text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCommandSend}
                className="rounded-md bg-indigo-500 px-3 py-1 text-xs text-white"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === "settings" && (
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <section className="rounded-2xl border border-slate-800 p-6">
            <h2 className="text-lg font-semibold">Permissions & Modes</h2>
            {config && (
              <div className="mt-4 space-y-3 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.permissions.tools_enabled}
                    onChange={(event) =>
                      setConfig({
                        ...config,
                        permissions: {
                          ...config.permissions,
                          tools_enabled: event.target.checked,
                        },
                      })
                    }
                  />
                  Tools enabled
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.permissions.terminal_enabled}
                    onChange={(event) =>
                      setConfig({
                        ...config,
                        permissions: {
                          ...config.permissions,
                          terminal_enabled: event.target.checked,
                        },
                      })
                    }
                  />
                  Terminal access (allowlist only)
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.voice.enabled}
                    onChange={(event) =>
                      setConfig({
                        ...config,
                        voice: { ...config.voice, enabled: event.target.checked },
                      })
                    }
                  />
                  Voice enabled
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={ttsEnabled}
                    onChange={(event) => setTtsEnabled(event.target.checked)}
                  />
                  Auto TTS playback
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.voice.hands_free}
                    onChange={(event) =>
                      setConfig({
                        ...config,
                        voice: { ...config.voice, hands_free: event.target.checked },
                      })
                    }
                  />
                  Hands-free mode
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.voice.wake_word_enabled}
                    onChange={(event) =>
                      setConfig({
                        ...config,
                        voice: {
                          ...config.voice,
                          wake_word_enabled: event.target.checked,
                        },
                      })
                    }
                  />
                  Wake word gate
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.rag.enabled}
                    onChange={(event) =>
                      setConfig({
                        ...config,
                        rag: { ...config.rag, enabled: event.target.checked },
                      })
                    }
                  />
                  RAG enabled
                </label>
              </div>
            )}
          </section>
          <section className="rounded-2xl border border-slate-800 p-6">
            <h2 className="text-lg font-semibold">Routing Rules</h2>
            <textarea
              className="mt-4 h-64 w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs"
              value={routerJson}
              onChange={(event) => setRouterJson(event.target.value)}
            />
            <button
              onClick={handleSaveConfig}
              className="mt-3 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white"
            >
              Save routing config
            </button>
            <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="text-xs text-slate-400">Test router</div>
              <input
                className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs"
                placeholder="Sample prompt for routing"
                value={routerTestInput}
                onChange={(event) => setRouterTestInput(event.target.value)}
              />
              <button
                onClick={handleRouterTest}
                className="mt-2 rounded-md bg-slate-800 px-3 py-1 text-xs text-slate-200"
              >
                Test
              </button>
              {routerTestResult && (
                <div className="mt-2 text-xs text-slate-500">{routerTestResult}</div>
              )}
            </div>
          </section>
          <section className="rounded-2xl border border-slate-800 p-6">
            <h2 className="text-lg font-semibold">RAG Ingestion</h2>
            <p className="mt-2 text-xs text-slate-400">
              Add a local file or folder path. Requires file read permission.
            </p>
            <input
              className="mt-4 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              placeholder="C:\\Users\\me\\Docs"
              value={ingestPath}
              onChange={(event) => setIngestPath(event.target.value)}
            />
            <button
              onClick={handleIngest}
              className="mt-3 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white"
            >
              Ingest
            </button>
            {ingestStatus && (
              <div className="mt-2 text-xs text-slate-500">{ingestStatus}</div>
            )}
          </section>
        </div>
      )}

      {activeTab === "logs" && (
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <section className="rounded-2xl border border-slate-800 p-4">
            <h2 className="text-sm font-semibold">Audit</h2>
            <pre className="mt-3 h-80 overflow-auto text-xs text-slate-300">
              {JSON.stringify(auditLogs, null, 2)}
            </pre>
          </section>
          <section className="rounded-2xl border border-slate-800 p-4">
            <h2 className="text-sm font-semibold">Dreams</h2>
            <pre className="mt-3 h-80 overflow-auto text-xs text-slate-300">
              {JSON.stringify(dreamLogs, null, 2)}
            </pre>
          </section>
          <section className="rounded-2xl border border-slate-800 p-4">
            <h2 className="text-sm font-semibold">Reflections</h2>
            <pre className="mt-3 h-80 overflow-auto text-xs text-slate-300">
              {JSON.stringify(reflectionLogs, null, 2)}
            </pre>
          </section>
        </div>
      )}
    </div>
  );
}
