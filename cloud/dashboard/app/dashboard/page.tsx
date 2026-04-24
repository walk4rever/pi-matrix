"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { supabase } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://relay.air7.fun/pm/api";

type DeviceItem = {
  id: string;
  name: string;
  type: string;
  status: string;
  version: string;
  last_seen: string;
  detail: string;
};

type CapabilityItem = {
  capability: string;
  capability_status: string;
  credential: string;
  owner: string;
  credential_status: string;
  action: string;
};

type MemoryFileItem = {
  file: string;
  role: string;
  updated_at: string;
  summary: string;
  status: string;
};

type RunLogItem = {
  time: string | null;
  task: string;
  status: string;
  reason: string;
  output: string;
  retryable: boolean;
};

type DashboardOverview = {
  profile: {
    email: string | null;
    user_id: string;
  };
  summary: {
    device_total: number;
    online_devices: number;
    capability_total: number;
    capability_ready: number;
  };
  devices: DeviceItem[];
  capabilities: CapabilityItem[];
  memory_files: MemoryFileItem[];
  run_logs: RunLogItem[];
};

type ExecutionLogsResponse = {
  items: RunLogItem[];
  total: number;
  page: number;
  page_size: number;
};

function tone(status: string): string {
  if (status === "可用" || status === "已配置" || status === "成功" || status === "运行中" || status === "已启用") return "ok";
  if (status === "离线") return "warn";
  if (status === "不可用" || status === "未配置" || status === "失败") return "danger";
  return "neutral";
}

function formatLogTime(value: string | null): string {
  if (!value) return "-";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(dt);
}

export default function DashboardPage() {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [email, setEmail] = useState("");
  const [profileName, setProfileName] = useState("用户");
  const [sessionToken, setSessionToken] = useState("");
  const [runLogs, setRunLogs] = useState<RunLogItem[]>([]);
  const [logPage, setLogPage] = useState(1);
  const [logPageSize] = useState(10);
  const [logTotal, setLogTotal] = useState(0);
  const [logLoading, setLogLoading] = useState(false);
  const profileRef = useRef<HTMLDivElement | null>(null);
  const totalLogPages = Math.max(1, Math.ceil(logTotal / logPageSize));

  // Memory files (USER.md / MEMORY.md)
  const [memoryFiles, setMemoryFiles] = useState<Record<string, string>>({ USER: "", MEMORY: "" });
  const [memoryModal, setMemoryModal] = useState<{ key: string; editing: boolean } | null>(null);
  const [editMemoryContent, setEditMemoryContent] = useState("");
  const [memorySaving, setMemorySaving] = useState(false);
  const [memoryError, setMemoryError] = useState("");

  // SOUL.md
  const [soulContent, setSoulContent] = useState("");
  const [soulEditing, setSoulEditing] = useState(false);
  const [editSoulContent, setEditSoulContent] = useState("");
  const [soulSaving, setSoulSaving] = useState(false);
  const [soulError, setSoulError] = useState("");

  // Edit profile modal
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");

  // Change password modal
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  async function loadRunLogs(accessToken: string, page: number) {
    setLogLoading(true);
    try {
      const resp = await fetch(
        `${API_URL}/dashboard/execution-logs?page=${page}&page_size=${logPageSize}`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          cache: "no-store",
        }
      );
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const dataJson = (await resp.json()) as ExecutionLogsResponse;
      setRunLogs(dataJson.items || []);
      setLogTotal(dataJson.total || 0);
      setLogPage(dataJson.page || page);
    } finally {
      setLogLoading(false);
    }
  }

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!profileRef.current) return;
      if (!profileRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError("");

      const { data } = await supabase.auth.getSession();
      const session = data.session;
      if (!session) {
        router.replace("/login");
        return;
      }
      setSessionToken(session.access_token);

      const userEmail = session.user.email ?? "";
      const userName = String(session.user.user_metadata?.full_name ?? "").trim();

      if (!mounted) return;
      setEmail(userEmail);
      setProfileName(userName || userEmail.split("@")[0] || "用户");

      try {
        const resp = await fetch(`${API_URL}/dashboard/overview`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
          cache: "no-store",
        });

        if (resp.status === 401) {
          await supabase.auth.signOut();
          router.replace("/login");
          return;
        }

        if (!resp.ok) {
          const body = await resp.text();
          throw new Error(body || `HTTP ${resp.status}`);
        }

        const dataJson = (await resp.json()) as DashboardOverview;
        if (!mounted) return;
        setOverview(dataJson);
        await loadRunLogs(session.access_token, 1);

        // Load SOUL.md + memory files independently so one failure does not block the others.
        const fileRequests = [
          {
            url: `${API_URL}/dashboard/soul`,
            apply: (content: string) => setSoulContent(content),
          },
          {
            url: `${API_URL}/dashboard/memory/USER`,
            apply: (content: string) => setMemoryFiles((prev) => ({ ...prev, USER: content })),
          },
          {
            url: `${API_URL}/dashboard/memory/MEMORY`,
            apply: (content: string) => setMemoryFiles((prev) => ({ ...prev, MEMORY: content })),
          },
        ];

        await Promise.all(
          fileRequests.map(async ({ url, apply }) => {
            try {
              const resp = await fetch(url, {
                headers: { Authorization: `Bearer ${session.access_token}` },
                cache: "no-store",
              });
              if (!resp.ok) return;
              const j = (await resp.json()) as { content?: string };
              if (!mounted) return;
              apply(j.content ?? "");
            } catch {
              // non-critical
            }
          })
        );
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "加载失败，请稍后重试。");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [router]);

  async function onLogout() {
    await supabase.auth.signOut();
    router.replace("/");
  }

  function onOpenProfileModal() {
    setEditName(profileName);
    setProfileError("");
    setProfileModalOpen(true);
    setMenuOpen(false);
  }

  async function onSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    const name = editName.trim();
    if (!name) return;
    setProfileSaving(true);
    setProfileError("");
    const { error: updateError } = await supabase.auth.updateUser({
      data: { full_name: name },
    });
    setProfileSaving(false);
    if (updateError) {
      setProfileError(updateError.message || "保存失败，请重试。");
      return;
    }
    setProfileName(name);
    setProfileModalOpen(false);
  }

  function onOpenPasswordModal() {
    setNewPassword("");
    setConfirmPassword("");
    setPasswordError("");
    setPasswordModalOpen(true);
    setMenuOpen(false);
  }

  function onOpenMemoryModal(key: string, editing: boolean) {
    setEditMemoryContent(memoryFiles[key] ?? "");
    setMemoryError("");
    setMemoryModal({ key, editing });
  }

  function onCloseMemoryModal() {
    setMemoryModal(null);
    setMemoryError("");
  }

  async function onSaveMemoryFile(e: React.FormEvent) {
    e.preventDefault();
    if (!memoryModal) return;
    setMemorySaving(true);
    setMemoryError("");
    try {
      const resp = await fetch(`${API_URL}/dashboard/memory/${memoryModal.key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
        body: JSON.stringify({ content: editMemoryContent }),
      });
      if (!resp.ok) throw new Error((await resp.text()) || `HTTP ${resp.status}`);
      setMemoryFiles((prev) => ({ ...prev, [memoryModal.key]: editMemoryContent }));
      setMemoryModal(null);
    } catch (err) {
      setMemoryError(err instanceof Error ? err.message : "保存失败，请重试。");
    } finally {
      setMemorySaving(false);
    }
  }

  function onOpenSoulEditor() {
    setEditSoulContent(soulContent);
    setSoulError("");
    setSoulEditing(true);
  }

  function onCancelSoulEditor() {
    setSoulEditing(false);
    setSoulError("");
  }

  async function onSaveSoul(e: React.FormEvent) {
    e.preventDefault();
    setSoulSaving(true);
    setSoulError("");
    try {
      const resp = await fetch(`${API_URL}/dashboard/soul`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ content: editSoulContent }),
      });
      if (!resp.ok) {
        const body = await resp.text();
        throw new Error(body || `HTTP ${resp.status}`);
      }
      setSoulContent(editSoulContent);
      setSoulEditing(false);
    } catch (err) {
      setSoulError(err instanceof Error ? err.message : "保存失败，请重试。");
    } finally {
      setSoulSaving(false);
    }
  }

  async function onSavePassword(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) {
      setPasswordError("密码至少需要 8 位。");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("两次密码输入不一致。");
      return;
    }
    setPasswordSaving(true);
    setPasswordError("");
    const { error: updateError } = await supabase.auth.updateUser({ password: newPassword });
    setPasswordSaving(false);
    if (updateError) {
      setPasswordError(updateError.message || "修改失败，请重试。");
      return;
    }
    setPasswordModalOpen(false);
  }

  const avatar = (profileName || "U").slice(0, 1).toUpperCase();

  async function onRefreshLogs() {
    if (!sessionToken) return;
    await loadRunLogs(sessionToken, 1);
  }

  async function onChangeLogPage(nextPage: number) {
    if (!sessionToken) return;
    if (nextPage < 1 || nextPage > totalLogPages) return;
    await loadRunLogs(sessionToken, nextPage);
  }

  return (
    <>
      <header className="workspace-header">
        <div className="container nav-inner">
          <Link href="/" className="brand workspace-brand-link">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="pi-matrix" width={28} height={28} />
            <span className="brand-name">pi<span>-matrix</span></span>
          </Link>
          <div className="workspace-profile-wrap" ref={profileRef}>
            <button
              className="workspace-profile"
              onClick={() => setMenuOpen((v) => !v)}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
            >
              <span className="workspace-avatar">{avatar}</span>
              <div>
                <p className="workspace-profile-name">{profileName}</p>
                <p className="workspace-profile-sub">{email || "-"}</p>
              </div>
            </button>

            {menuOpen && (
              <div className="workspace-profile-menu" role="menu">
                <button className="workspace-profile-menu-item" role="menuitem" onClick={onOpenProfileModal}>编辑资料</button>
                <button className="workspace-profile-menu-item" role="menuitem" onClick={onOpenPasswordModal}>修改密码</button>
                <button className="workspace-profile-menu-item danger" role="menuitem" onClick={onLogout}>退出登录</button>
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="workspace-page">

      {loading && (
        <section className="workspace-card">
          <p className="workspace-card-desc">正在加载控制台数据...</p>
        </section>
      )}

      {error && !loading && (
        <section className="workspace-card">
          <p className="workspace-card-desc" style={{ color: "#a8332c" }}>加载失败：{error}</p>
        </section>
      )}

      {!loading && !error && overview && (
        <>
          <section className="workspace-card">
            <h1 className="workspace-card-title">设备状态</h1>
            <p className="workspace-card-desc">
              云端/端侧设备：在线 {overview.summary.online_devices} / 总计 {overview.summary.device_total}
            </p>
            <div className="workspace-grid-two">
              {overview.devices.length > 0 ? (
                overview.devices.map((d) => (
                  <article key={d.id} className="workspace-capability-item">
                    <div>
                      <p className="workspace-item-title">{d.name}</p>
                      <p className="workspace-item-hint">{d.type} · 版本 {d.version}</p>
                      <p className="workspace-item-hint">最后心跳：{d.last_seen}</p>
                      <p className="workspace-item-hint">{d.detail}</p>
                    </div>
                    <span className={`workspace-pill ${tone(d.status)}`}>{d.status}</span>
                  </article>
                ))
              ) : (
                <article className="workspace-capability-item">
                  <p className="workspace-item-hint">暂无设备数据。</p>
                </article>
              )}
            </div>
          </section>

          <section className="workspace-card">
            <h2 className="workspace-card-title">能力凭证</h2>
            <p className="workspace-card-desc">
              可用能力 {overview.summary.capability_ready} / {overview.summary.capability_total}
            </p>
            <div className="workspace-table-wrap">
              <table className="workspace-table">
                <thead>
                  <tr>
                    <th>能力</th>
                    <th>能力状态</th>
                    <th>凭证</th>
                    <th>归属</th>
                    <th>凭证状态</th>
                    <th>动作</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.capabilities.map((row) => (
                    <tr key={row.capability}>
                      <td>{row.capability}</td>
                      <td><span className={`workspace-pill ${tone(row.capability_status)}`}>{row.capability_status}</span></td>
                      <td>{row.credential}</td>
                      <td>{row.owner}</td>
                      <td><span className={`workspace-pill ${tone(row.credential_status)}`}>{row.credential_status}</span></td>
                      <td><button className="workspace-action-link">{row.action}</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="workspace-card">
            <div className="workspace-card-head">
              <h2 className="workspace-card-title">人格设定</h2>
              {!soulEditing && (
                <button className="workspace-text-btn" onClick={onOpenSoulEditor} title="编辑 SOUL.md">
                  编辑
                </button>
              )}
            </div>
            <p className="workspace-card-desc">
              定义 Hermes 的行为准则、语气风格与工作方式（SOUL.md）。直接影响"懂你"程度，建议亲自调整。
            </p>
            {!soulEditing ? (
              <div className={`soul-preview${soulContent ? "" : " empty"}`}>
                {soulContent
                  ? soulContent.split("\n").slice(0, 6).join("\n") + (soulContent.split("\n").length > 6 ? "\n…" : "")
                  : "尚未设置人格文件。点击「编辑」开始定义 Hermes 的性格。"}
              </div>
            ) : (
              <form onSubmit={onSaveSoul}>
                <textarea
                  className="soul-textarea"
                  value={editSoulContent}
                  onChange={(e) => setEditSoulContent(e.target.value)}
                  placeholder="用自然语言描述 Hermes 的人格、行为准则与语气风格…"
                  autoFocus
                />
                {soulError && <p className="form-error" style={{ marginBottom: "0.5rem" }}>{soulError}</p>}
                <div className="modal-actions" style={{ justifyContent: "flex-start" }}>
                  <button type="button" className="btn-secondary" onClick={onCancelSoulEditor}>取消</button>
                  <button type="submit" className="btn-primary" disabled={soulSaving}>
                    {soulSaving ? "保存中..." : "保存"}
                  </button>
                </div>
              </form>
            )}
          </section>

          <section className="workspace-card">
            <h2 className="workspace-card-title">记忆管理</h2>
            <p className="workspace-card-desc">Hermes 自动维护的两个核心记忆文件，影响"懂你"程度，可手动查看或纠正。</p>
            <div className="workspace-grid-two">
              {overview.memory_files.map((item) => {
                const fileKey = item.file.replace(".md", "").toUpperCase();
                const content = memoryFiles[fileKey] ?? "";
                const preview = content
                  ? content.split("\n").slice(0, 4).join("\n") + (content.split("\n").length > 4 ? "\n…" : "")
                  : "尚无内容";
                return (
                  <article key={item.file} className="workspace-capability-item" style={{ flexDirection: "column", alignItems: "flex-start", gap: "0.6rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "flex-start" }}>
                      <div>
                        <p className="workspace-item-title">{item.file}</p>
                        <p className="workspace-item-hint">{item.role}</p>
                        <p className="workspace-item-hint">最近更新：{item.updated_at}</p>
                      </div>
                      <span className={`workspace-pill ${tone(item.status)}`}>{item.status}</span>
                    </div>
                    <div className={`soul-preview${content ? "" : " empty"}`} style={{ marginBottom: 0, width: "100%", boxSizing: "border-box" }}>
                      {preview}
                    </div>
                    <div className="workspace-inline-actions">
                      <button className="workspace-action-link" onClick={() => onOpenMemoryModal(fileKey, false)}>查看文件</button>
                      <button className="workspace-action-link" onClick={() => onOpenMemoryModal(fileKey, true)}>编辑文件</button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="workspace-card">
            <div className="workspace-card-head">
              <h2 className="workspace-card-title">执行日志</h2>
              <button
                className="workspace-icon-btn"
                onClick={onRefreshLogs}
                disabled={logLoading}
                title="刷新最新日志"
                aria-label="刷新最新日志"
              >
                {logLoading ? "…" : "↻"}
              </button>
            </div>
            <p className="workspace-card-desc">最近执行事件（来自当前可用存储）</p>
            <div className="workspace-table-wrap">
              <table className="workspace-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>任务</th>
                    <th>状态</th>
                    <th>失败原因 / 结果</th>
                    <th>产物</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {runLogs.length > 0 ? (
                    runLogs.map((log) => (
                      <tr key={`${log.time}-${log.task}`}>
                        <td>{formatLogTime(log.time)}</td>
                        <td>{log.task}</td>
                        <td><span className={`workspace-pill ${tone(log.status)}`}>{log.status}</span></td>
                        <td>{log.reason}</td>
                        <td>{log.output === "-" ? "-" : <button className="workspace-action-link">{log.output}</button>}</td>
                        <td>{log.retryable ? <button className="workspace-action-link">重试</button> : "-"}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td>-</td>
                      <td>暂无执行日志</td>
                      <td><span className="workspace-pill neutral">-</span></td>
                      <td>-</td>
                      <td>-</td>
                      <td>-</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="workspace-pagination">
              <button
                className="workspace-page-btn"
                onClick={() => onChangeLogPage(logPage - 1)}
                disabled={logLoading || logPage <= 1}
              >
                上一页
              </button>
              <span className="workspace-page-text">
                第 {logPage} / {totalLogPages} 页
              </span>
              <button
                className="workspace-page-btn"
                onClick={() => onChangeLogPage(logPage + 1)}
                disabled={logLoading || logPage >= totalLogPages}
              >
                下一页
              </button>
            </div>
          </section>
        </>
      )}
    </main>

    {memoryModal && (
      <div className="modal-overlay" onClick={onCloseMemoryModal}>
        <div className="modal-card" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
          <p className="modal-title">
            {memoryModal.key === "USER" ? "USER.md — 用户画像" : "MEMORY.md — 工作记忆"}
          </p>
          {memoryModal.editing ? (
            <form onSubmit={onSaveMemoryFile}>
              <textarea
                className="soul-textarea"
                value={editMemoryContent}
                onChange={(e) => setEditMemoryContent(e.target.value)}
                placeholder="文件内容为空，可手动填入初始内容…"
                autoFocus
              />
              {memoryError && <p className="form-error" style={{ marginBottom: "0.5rem" }}>{memoryError}</p>}
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={onCloseMemoryModal}>取消</button>
                <button type="submit" className="btn-primary" disabled={memorySaving}>
                  {memorySaving ? "保存中..." : "保存"}
                </button>
              </div>
            </form>
          ) : (
            <>
              <div className={`soul-preview${memoryFiles[memoryModal.key] ? "" : " empty"}`} style={{ maxHeight: 360, overflowY: "auto" }}>
                {memoryFiles[memoryModal.key] || "该文件暂无内容。"}
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={onCloseMemoryModal}>关闭</button>
                <button type="button" className="btn-primary" onClick={() => setMemoryModal({ ...memoryModal, editing: true })}>
                  编辑
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    )}

    {profileModalOpen && (
      <div className="modal-overlay" onClick={() => setProfileModalOpen(false)}>
        <div className="modal-card" onClick={(e) => e.stopPropagation()}>
          <p className="modal-title">编辑资料</p>
          <form onSubmit={onSaveProfile}>
            <div className="form-group">
              <div>
                <label className="form-label">显示名称</label>
                <input
                  type="text"
                  className="form-input"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="请输入名称"
                  required
                  autoFocus
                />
              </div>
              {profileError && <p className="form-error">{profileError}</p>}
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setProfileModalOpen(false)}>取消</button>
              <button type="submit" className="btn-primary" disabled={profileSaving}>
                {profileSaving ? "保存中..." : "保存"}
              </button>
            </div>
          </form>
        </div>
      </div>
    )}

    {passwordModalOpen && (
      <div className="modal-overlay" onClick={() => setPasswordModalOpen(false)}>
        <div className="modal-card" onClick={(e) => e.stopPropagation()}>
          <p className="modal-title">修改密码</p>
          <form onSubmit={onSavePassword}>
            <div className="form-group">
              <div>
                <label className="form-label">新密码</label>
                <input
                  type="password"
                  className="form-input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="至少 8 位"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="form-label">确认密码</label>
                <input
                  type="password"
                  className="form-input"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="再次输入密码"
                  required
                />
              </div>
              {passwordError && <p className="form-error">{passwordError}</p>}
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setPasswordModalOpen(false)}>取消</button>
              <button type="submit" className="btn-primary" disabled={passwordSaving}>
                {passwordSaving ? "修改中..." : "确认修改"}
              </button>
            </div>
          </form>
        </div>
      </div>
    )}
    </>
  );
}
