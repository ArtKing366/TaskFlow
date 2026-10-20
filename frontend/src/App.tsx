import { useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, Blocks,
  CalendarDays, Check, CheckCheck, ChevronDown, CircleAlert, CircleDashed, Clock3,
  Code2, Command, Ellipsis, ExternalLink, FileClock, Filter, FolderKanban, Globe,
  LayoutDashboard, Link2, ListTodo, LoaderCircle, LockKeyhole, LogOut, Mail,
  Menu, MoreHorizontal, Pencil, Plus, Search, Settings2, ShieldCheck, Sparkles,
  Trash2, Users, Webhook as WebhookIcon, Workflow, X, Zap,
} from 'lucide-react';
import { api, ApiError, jsonBody, newIdempotencyKey } from './api';
import type {
  AuditLog, Automation, Notification, PageKey, Project, Role, Task, TaskPriority,
  TaskStatus, User, Webhook, WebhookEvent, Workspace,
} from './types';

const NAV_ITEMS: { key: PageKey; label: string; icon: typeof LayoutDashboard; group: 'WORKSPACE' | 'AUTOMATION' }[] = [
  { key: 'overview', label: 'Overview', icon: LayoutDashboard, group: 'WORKSPACE' },
  { key: 'projects', label: 'Projects', icon: FolderKanban, group: 'WORKSPACE' },
  { key: 'tasks', label: 'Task board', icon: ListTodo, group: 'WORKSPACE' },
  { key: 'activity', label: 'Activity log', icon: FileClock, group: 'WORKSPACE' },
  { key: 'notifications', label: 'Notifications', icon: Bell, group: 'WORKSPACE' },
  { key: 'automations', label: 'Automations', icon: Workflow, group: 'AUTOMATION' },
  { key: 'webhooks', label: 'Webhooks', icon: WebhookIcon, group: 'AUTOMATION' },
  { key: 'team', label: 'Team & access', icon: Users, group: 'AUTOMATION' },
];

const PAGE_META: Record<PageKey, { title: string; subtitle: string }> = {
  overview: { title: 'Overview', subtitle: 'Your workspace at a glance.' },
  projects: { title: 'Projects', subtitle: 'Organize work into focused projects.' },
  tasks: { title: 'Task board', subtitle: 'Move work forward, one task at a time.' },
  activity: { title: 'Activity log', subtitle: 'A traceable history of workspace changes.' },
  notifications: { title: 'Notifications', subtitle: 'Updates created for you by TaskFlow.' },
  automations: { title: 'Automations', subtitle: 'Turn repeated workflow steps into rules.' },
  webhooks: { title: 'Webhooks', subtitle: 'Send workspace events to external services.' },
  team: { title: 'Team & access', subtitle: 'Manage workspace membership and roles.' },
};

const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: 'To do',
  in_progress: 'In progress',
  done: 'Done',
};
const PRIORITY_LABEL: Record<TaskPriority, string> = { low: 'Low', medium: 'Medium', high: 'High' };
const ROLE_LABEL: Record<Role, string> = { owner: 'Owner', admin: 'Admin', member: 'Member', viewer: 'Viewer' };
const WEBHOOK_EVENTS: WebhookEvent[] = ['task.created', 'task.updated', 'task.completed', 'project.created'];

function dateLabel(date?: string | null): string {
  if (!date) return 'No deadline';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return 'No deadline';
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(parsed);
}

function timeLabel(date?: string | null): string {
  if (!date) return '—';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return '—';
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(parsed);
}

function isOverdue(task: Task): boolean {
  return Boolean(task.deadline && task.status !== 'done' && new Date(task.deadline).getTime() < Date.now());
}

function initials(value: string): string {
  return value.split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'TF';
}

function humanizeAction(action: string): string {
  return action.replaceAll('.', ' ').replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}

type ToastState = { message: string; kind: 'success' | 'error' | 'info' } | null;
type ModalState =
  | { type: 'workspace' }
  | { type: 'project'; item?: Project }
  | { type: 'task'; item?: Task }
  | { type: 'automation'; item?: Automation }
  | { type: 'webhook'; item?: Webhook }
  | null;

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('taskflow_token'));
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);
  const [page, setPage] = useState<PageKey>('overview');
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [authLoading, setAuthLoading] = useState(Boolean(localStorage.getItem('taskflow_token')));
  const [pageLoading, setPageLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [toast, setToast] = useState<ToastState>(null);
  const [modal, setModal] = useState<ModalState>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | 'all'>('all');
  const [projectFilter, setProjectFilter] = useState<number | 'all'>('all');
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const selectedWorkspace = workspaces.find((workspace) => workspace.id === workspaceId) ?? null;
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  const notify = (message: string, kind: 'success' | 'error' | 'info' = 'success') => setToast({ message, kind });
  const refresh = () => setRefreshKey((value) => value + 1);

  const clearSession = () => {
    localStorage.removeItem('taskflow_token');
    setToken(null);
    setUser(null);
    setWorkspaces([]);
    setWorkspaceId(null);
    setProjects([]);
    setTasks([]);
    setAutomations([]);
    setWebhooks([]);
    setNotifications([]);
    setAuditLogs([]);
  };

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    if (!token) {
      setAuthLoading(false);
      return;
    }
    let active = true;
    setAuthLoading(true);
    Promise.all([api<User>('/auth/me'), api<Workspace[]>('/workspaces')])
      .then(([currentUser, currentWorkspaces]) => {
        if (!active) return;
        setUser(currentUser);
        setWorkspaces(currentWorkspaces);
        setWorkspaceId((currentId) => currentWorkspaces.some((workspace) => workspace.id === currentId)
          ? currentId
          : currentWorkspaces[0]?.id ?? null);
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
        } else {
          notify(getErrorMessage(error), 'error');
        }
      })
      .finally(() => { if (active) setAuthLoading(false); });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!token || workspaceId === null) {
      setPageLoading(false);
      if (workspaceId === null) {
        setProjects([]);
        setTasks([]);
        setAutomations([]);
        setWebhooks([]);
        setAuditLogs([]);
        setNotifications([]);
      }
      return;
    }
    let active = true;
    const load = async () => {
      setPageLoading(true);
      try {
        if (page === 'overview' || page === 'projects' || page === 'tasks') {
          const result = await api<Project[]>(`/workspaces/${workspaceId}/projects/`);
          if (!active) return;
          setProjects(result);
          const taskGroups = await Promise.all(result.map(async (project) => {
            const items = await api<Task[]>(`/workspaces/${workspaceId}/projects/${project.id}/tasks`);
            return items.map((task) => ({ ...task, projectTitle: project.title }));
          }));
          if (!active) return;
          setTasks(taskGroups.flat());
        } else if (page === 'automations') {
          const result = await api<Automation[]>(`/workspaces/${workspaceId}/automations/`);
          if (active) setAutomations(result);
        } else if (page === 'webhooks') {
          const result = await api<Webhook[]>(`/workspaces/${workspaceId}/webhooks/`);
          if (active) setWebhooks(result);
        } else if (page === 'activity') {
          const result = await api<AuditLog[]>(`/workspaces/${workspaceId}/audit-logs/`);
          if (active) setAuditLogs(result);
        } else if (page === 'notifications') {
          const result = await api<Notification[]>(`/workspaces/${workspaceId}/notifications/`);
          if (active) setNotifications(result);
        }
      } catch (error) {
        if (active && error instanceof ApiError && error.status === 401) {
          clearSession();
          notify('Your session expired. Please sign in again.', 'info');
        } else if (active) {
          notify(getErrorMessage(error), 'error');
        }
      } finally {
        if (active) setPageLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [token, workspaceId, page, refreshKey]);

  const login = async (email: string, password: string, mode: 'login' | 'register') => {
    const credentials = { email, password };
    if (mode === 'register') {
      await api<User>('/auth/register', { method: 'POST', body: jsonBody(credentials) });
    }
    const response = await api<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST', body: jsonBody(credentials),
    });
    localStorage.setItem('taskflow_token', response.access_token);
    setToken(response.access_token);
    notify(mode === 'register' ? 'Account created. Welcome to TaskFlow.' : 'Welcome back.', 'success');
  };

  const createWorkspace = async (name: string) => {
    const workspace = await api<Workspace>('/workspaces', { method: 'POST', body: jsonBody({ name }) });
    setWorkspaces((current) => [...current, workspace]);
    setWorkspaceId(workspace.id);
    setModal(null);
    setPage('overview');
    notify('Workspace created. You are its owner.');
  };

  const saveProject = async (value: { title: string; description: string }, existing?: Project) => {
    if (workspaceId === null) return;
    if (existing) {
      await api<Project>(`/workspaces/${workspaceId}/projects/${existing.id}`, { method: 'PATCH', body: jsonBody(value) });
      notify('Project updated.');
    } else {
      await api<Project>(`/workspaces/${workspaceId}/projects/`, {
        method: 'POST',
        headers: { 'Idempotency-Key': newIdempotencyKey() },
        body: jsonBody({ ...value, workspace_id: workspaceId }),
      });
      notify('Project created.');
    }
    setModal(null);
    refresh();
  };

  const deleteProject = async (project: Project) => {
    if (workspaceId === null || !window.confirm(`Delete “${project.title}” and its tasks? This cannot be undone.`)) return;
    try {
      await api(`/workspaces/${workspaceId}/projects/${project.id}`, { method: 'DELETE' });
      notify('Project deleted.');
      if (selectedProjectId === project.id) setSelectedProjectId(null);
      refresh();
    } catch (error) { notify(getErrorMessage(error), 'error'); }
  };

  const saveTask = async (value: {
    title: string; description: string; status: TaskStatus; priority: TaskPriority;
    project_id: number; deadline: string | null; assignee_id: number | null;
  }, existing?: Task) => {
    if (workspaceId === null) return;
    const payload = {
      title: value.title,
      description: value.description,
      status: value.status,
      priority: value.priority,
      deadline: value.deadline,
      assignee_id: value.assignee_id,
    };
    if (existing) {
      await api<Task>(`/workspaces/${workspaceId}/tasks/${existing.id}`, { method: 'PATCH', body: jsonBody(payload) });
      notify('Task updated.');
    } else {
      await api<Task>(`/workspaces/${workspaceId}/projects/${value.project_id}/tasks`, {
        method: 'POST',
        headers: { 'Idempotency-Key': newIdempotencyKey() },
        body: jsonBody({ ...payload, project_id: value.project_id }),
      });
      notify('Task created.');
    }
    setModal(null);
    refresh();
  };

  const completeTask = async (task: Task) => {
    if (workspaceId === null) return;
    try {
      await api(`/workspaces/${workspaceId}/tasks/${task.id}/complete`, { method: 'PATCH' });
      notify(task.status === 'done' ? 'Task was already completed.' : 'Task completed. Automations and matching webhooks were evaluated.');
      refresh();
    } catch (error) { notify(getErrorMessage(error), 'error'); }
  };

  const moveTask = async (task: Task, status: TaskStatus) => {
    if (workspaceId === null || task.status === status) return;
    try {
      await api(`/workspaces/${workspaceId}/tasks/${task.id}`, { method: 'PATCH', body: jsonBody({ status }) });
      notify(`Task moved to ${STATUS_LABEL[status].toLowerCase()}.`);
      refresh();
    } catch (error) { notify(getErrorMessage(error), 'error'); }
  };

  const deleteTask = async (task: Task) => {
    if (workspaceId === null || !window.confirm(`Delete task “${task.title}”?`)) return;
    try {
      await api(`/workspaces/${workspaceId}/tasks/${task.id}`, { method: 'DELETE' });
      notify('Task deleted.');
      refresh();
    } catch (error) { notify(getErrorMessage(error), 'error'); }
  };

  const saveAutomation = async (value: {
    name: string; condition: { field: 'priority'; operator: 'eq'; value: TaskPriority } | null; is_active: boolean;
  }, existing?: Automation) => {
    if (workspaceId === null) return;
    const payload = {
      ...value,
      trigger: 'task.completed' as const,
      action: { type: 'send_notification' as const, recipients: 'workspace_members' as const },
    };
    if (existing) {
      await api<Automation>(`/workspaces/${workspaceId}/automations/${existing.id}`, { method: 'PATCH', body: jsonBody(payload) });
      notify('Automation updated.');
    } else {
      await api<Automation>(`/workspaces/${workspaceId}/automations/`, {
        method: 'POST', headers: { 'Idempotency-Key': newIdempotencyKey() }, body: jsonBody(payload),
      });
      notify('Automation created.');
    }
    setModal(null);
    refresh();
  };

  const deleteAutomation = async (item: Automation) => {
    if (workspaceId === null || !window.confirm(`Delete automation “${item.name}”?`)) return;
    try {
      await api(`/workspaces/${workspaceId}/automations/${item.id}`, { method: 'DELETE' });
      notify('Automation deleted.');
      refresh();
    } catch (error) { notify(getErrorMessage(error), 'error'); }
  };

  const saveWebhook = async (value: { url: string; events: WebhookEvent[]; is_active: boolean }, existing?: Webhook) => {
    if (workspaceId === null) return;
    if (existing) {
      await api<Webhook>(`/workspaces/${workspaceId}/webhooks/${existing.id}`, { method: 'PATCH', body: jsonBody(value) });
      notify('Webhook updated.');
    } else {
      await api<Webhook>(`/workspaces/${workspaceId}/webhooks/`, { method: 'POST', body: jsonBody({ url: value.url, events: value.events }) });
      notify('Webhook created.');
    }
    setModal(null);
    refresh();
  };

  const deleteWebhook = async (item: Webhook) => {
    if (workspaceId === null || !window.confirm(`Delete webhook for ${item.url}?`)) return;
    try {
      await api(`/workspaces/${workspaceId}/webhooks/${item.id}`, { method: 'DELETE' });
      notify('Webhook deleted.');
      refresh();
    } catch (error) { notify(getErrorMessage(error), 'error'); }
  };

  const goToTasksForProject = (projectId: number) => {
    setSelectedProjectId(projectId);
    setProjectFilter(projectId);
    setPage('tasks');
  };

  if (authLoading) return <FullScreenLoading />;
  if (!token || !user) return <AuthScreen onSubmit={login} />;

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="mobile-scrim" aria-label="Close menu" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Workflow size={19} strokeWidth={2.4} /></div>
          <div><div className="brand-name">taskflow<span>.</span></div><div className="brand-caption">WORKSPACE OS</div></div>
          <button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar"><X size={18} /></button>
        </div>

        <div className="workspace-picker-wrap">
          <div className="mini-label">CURRENT WORKSPACE</div>
          <div className="workspace-picker">
            <div className="workspace-symbol">{selectedWorkspace ? initials(selectedWorkspace.name).slice(0, 1) : 'W'}</div>
            <select
              aria-label="Select workspace"
              value={workspaceId ?? ''}
              onChange={(event) => { setWorkspaceId(event.target.value ? Number(event.target.value) : null); setSelectedProjectId(null); setProjectFilter('all'); setSidebarOpen(false); }}
            >
              <option value="" disabled>{workspaces.length ? 'Select workspace' : 'No workspace yet'}</option>
              {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
            </select>
            <ChevronDown size={14} className="picker-chevron" />
          </div>
          <button className="workspace-add" onClick={() => setModal({ type: 'workspace' })}><Plus size={14} /> New workspace</button>
        </div>

        <nav className="side-nav" aria-label="Main navigation">
          <div className="nav-group-label">WORKSPACE</div>
          {NAV_ITEMS.filter((item) => item.group === 'WORKSPACE').map((item) => <NavButton key={item.key} item={item} active={page === item.key} onClick={() => { setPage(item.key); setSidebarOpen(false); }} />)}
          <div className="nav-group-label nav-group-gap">BUILD & AUTOMATE</div>
          {NAV_ITEMS.filter((item) => item.group === 'AUTOMATION').map((item) => <NavButton key={item.key} item={item} active={page === item.key} onClick={() => { setPage(item.key); setSidebarOpen(false); }} />)}
        </nav>

        <div className="sidebar-bottom">
          <div className="status-card">
            <div className="status-card-icon"><ShieldCheck size={17} /></div>
            <div className="status-copy"><strong>Workspace secured</strong><span>Role-based access enabled</span></div>
            <span className="status-dot" />
          </div>
          <div className="sidebar-user">
            <div className="avatar avatar-small">{initials(user.email)}</div>
            <div className="sidebar-user-meta"><strong>{user.email.split('@')[0]}</strong><span>{user.email}</span></div>
            <button className="icon-button logout-button" onClick={() => { clearSession(); notify('Signed out.', 'info'); }} title="Sign out" aria-label="Sign out"><LogOut size={16} /></button>
          </div>
        </div>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={20} /></button>
            <div className="breadcrumbs"><span>Workspace</span><span className="crumb-separator">/</span><strong>{PAGE_META[page].title}</strong></div>
          </div>
          <div className="topbar-right">
            <label className="global-search"><Search size={16} /><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') setPage('tasks'); }} placeholder="Search tasks..." aria-label="Search tasks" /><kbd>Enter</kbd></label>
            <button className="icon-button notification-button" onClick={() => setPage('notifications')} title="Notifications" aria-label="Notifications"><Bell size={18} />{unreadCount > 0 && <span className="notification-count">{unreadCount > 9 ? '9+' : unreadCount}</span>}</button>
            <div className="topbar-divider" />
            <div className="top-user"><div className="avatar">{initials(user.email)}</div><div className="top-user-text"><strong>{user.email.split('@')[0]}</strong><span>Workspace member</span></div></div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading-row">
            <div><div className="eyebrow">{selectedWorkspace?.name ?? 'GET STARTED'}</div><h1>{PAGE_META[page].title}</h1><p>{PAGE_META[page].subtitle}</p></div>
            <div className="page-actions">
              <button className="button button-ghost" onClick={refresh} disabled={workspaceId === null || pageLoading}><Activity size={16} /> Refresh</button>
              {page === 'projects' && <button className="button button-primary" onClick={() => setModal({ type: 'project' })} disabled={workspaceId === null}><Plus size={17} /> New project</button>}
              {page === 'tasks' && <button className="button button-primary" onClick={() => setModal({ type: 'task' })} disabled={!projects.length}><Plus size={17} /> New task</button>}
              {page === 'automations' && <button className="button button-primary" onClick={() => setModal({ type: 'automation' })} disabled={workspaceId === null}><Plus size={17} /> New automation</button>}
              {page === 'webhooks' && <button className="button button-primary" onClick={() => setModal({ type: 'webhook' })} disabled={workspaceId === null}><Plus size={17} /> Add webhook</button>}
            </div>
          </div>

          {workspaceId === null ? (
            <WorkspaceWelcome onCreate={() => setModal({ type: 'workspace' })} />
          ) : pageLoading ? (
            <PageLoading />
          ) : (
            <>
              {page === 'overview' && <OverviewPage projects={projects} tasks={tasks} onNewProject={() => setModal({ type: 'project' })} onNewTask={() => setModal({ type: 'task' })} onOpenProject={goToTasksForProject} onOpenTasks={() => setPage('tasks')} />}
              {page === 'projects' && <ProjectsPage projects={projects} tasks={tasks} onCreate={() => setModal({ type: 'project' })} onEdit={(item) => setModal({ type: 'project', item })} onDelete={deleteProject} onOpen={goToTasksForProject} />}
              {page === 'tasks' && <TasksPage tasks={tasks} projects={projects} searchQuery={searchQuery} statusFilter={statusFilter} priorityFilter={priorityFilter} projectFilter={projectFilter} setStatusFilter={setStatusFilter} setPriorityFilter={setPriorityFilter} setProjectFilter={setProjectFilter} onEdit={(item) => setModal({ type: 'task', item })} onComplete={completeTask} onDelete={deleteTask} onMove={moveTask} onCreate={() => setModal({ type: 'task' })} onCreateProject={() => setModal({ type: 'project' })} />}
              {page === 'automations' && <AutomationsPage items={automations} onCreate={() => setModal({ type: 'automation' })} onEdit={(item) => setModal({ type: 'automation', item })} onDelete={deleteAutomation} onToggle={async (item) => { try { await api(`/workspaces/${workspaceId}/automations/${item.id}`, { method: 'PATCH', body: jsonBody({ is_active: !item.is_active }) }); notify(item.is_active ? 'Automation paused.' : 'Automation activated.'); refresh(); } catch (error) { notify(getErrorMessage(error), 'error'); } }} />}
              {page === 'webhooks' && <WebhooksPage items={webhooks} onCreate={() => setModal({ type: 'webhook' })} onEdit={(item) => setModal({ type: 'webhook', item })} onDelete={deleteWebhook} onToggle={async (item) => { try { await api(`/workspaces/${workspaceId}/webhooks/${item.id}`, { method: 'PATCH', body: jsonBody({ is_active: !item.is_active }) }); notify(item.is_active ? 'Webhook paused.' : 'Webhook activated.'); refresh(); } catch (error) { notify(getErrorMessage(error), 'error'); } }} />}
              {page === 'activity' && <ActivityPage items={auditLogs} />}
              {page === 'notifications' && <NotificationsPage items={notifications} />}
              {page === 'team' && <TeamPage workspaceId={workspaceId} onSuccess={(message) => { notify(message); refresh(); }} />}
            </>
          )}
        </div>
        <footer className="app-footer"><span><span className="footer-dot" /> All systems connected</span><span>TaskFlow API <span className="footer-version">v1.0</span></span></footer>
      </main>

      {modal?.type === 'workspace' && <WorkspaceModal onClose={() => setModal(null)} onSave={createWorkspace} />}
      {modal?.type === 'project' && <ProjectModal existing={modal.item} onClose={() => setModal(null)} onSave={(value) => saveProject(value, modal.item)} />}
      {modal?.type === 'task' && <TaskModal existing={modal.item} projects={projects} defaultProjectId={projectFilter !== 'all' ? projectFilter : selectedProjectId ?? projects[0]?.id ?? null} onClose={() => setModal(null)} onSave={(value) => saveTask(value, modal.item)} />}
      {modal?.type === 'automation' && <AutomationModal existing={modal.item} onClose={() => setModal(null)} onSave={(value) => saveAutomation(value, modal.item)} />}
      {modal?.type === 'webhook' && <WebhookModal existing={modal.item} onClose={() => setModal(null)} onSave={(value) => saveWebhook(value, modal.item)} />}
      {toast && <Toast toast={toast} onClose={() => setToast(null)} />}
    </div>
  );
}

function NavButton({ item, active, onClick }: { item: typeof NAV_ITEMS[number]; active: boolean; onClick: () => void }) {
  const Icon = item.icon;
  return <button className={`nav-item ${active ? 'nav-item-active' : ''}`} onClick={onClick}><Icon size={18} strokeWidth={active ? 2.2 : 1.8} /><span>{item.label}</span>{item.key === 'automations' && <span className="nav-new-dot" />}</button>;
}

function FullScreenLoading() {
  return <div className="full-screen-loading"><div className="brand-mark brand-mark-large"><Workflow size={22} /></div><LoaderCircle className="spinner" size={20} /><span>Connecting to TaskFlow...</span></div>;
}

function AuthScreen({ onSubmit }: { onSubmit: (email: string, password: string, mode: 'login' | 'register') => Promise<void> }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true); setError('');
    try { await onSubmit(email.trim(), password, mode); }
    catch (err) { setError(getErrorMessage(err)); }
    finally { setBusy(false); }
  };
  return (
    <div className="auth-shell">
      <section className="auth-showcase">
        <div className="auth-brand"><div className="brand-mark"><Workflow size={20} /></div><span>taskflow<span className="brand-period">.</span></span></div>
        <div className="auth-showcase-content">
          <div className="auth-kicker"><Sparkles size={14} /> THE WORKFLOW PLATFORM</div>
          <h1>Good work<br />happens <em>in flow.</em></h1>
          <p>One calm place to plan projects, move tasks forward, and automate the busywork.</p>
          <div className="auth-feature-list"><div><span><Check size={15} /></span> Projects and tasks, connected</div><div><span><Check size={15} /></span> Automations that do the follow-up</div><div><span><Check size={15} /></span> Every important action traceable</div></div>
          <div className="auth-product-preview">
            <div className="preview-top"><div className="preview-dots"><span /><span /><span /></div><span>Workspace pulse</span><span className="preview-live"><i /> Live</span></div>
            <div className="preview-stat-row"><div><span>Tasks completed</span><strong>24 <small>+18%</small></strong></div><div><span>Active projects</span><strong>08</strong></div><div><span>Automations</span><strong>12</strong></div></div>
            <div className="preview-bars"><i style={{ height: '35%' }} /><i style={{ height: '56%' }} /><i style={{ height: '43%' }} /><i style={{ height: '75%' }} /><i style={{ height: '50%' }} /><i style={{ height: '91%' }} /><i style={{ height: '64%' }} /><i style={{ height: '82%' }} /><i style={{ height: '69%' }} /><i style={{ height: '100%' }} /><i style={{ height: '77%' }} /><i style={{ height: '90%' }} /></div>
          </div>
        </div>
        <div className="auth-showcase-footer"><span>Built for teams that care about momentum.</span><span>© TaskFlow 2026</span></div>
      </section>
      <section className="auth-panel">
        <div className="auth-panel-inner">
          <div className="auth-mobile-title"><div className="brand-mark"><Workflow size={20} /></div><span>taskflow<span className="brand-period">.</span></span></div>
          <div className="auth-panel-top"><span className="auth-panel-label">YOUR WORKSPACE AWAITS</span><div className="auth-shield"><LockKeyhole size={17} /></div></div>
          <h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
          <p className="auth-subtitle">{mode === 'login' ? 'Sign in to pick up where your team left off.' : 'Set up your account and get your workspace moving.'}</p>
          <div className="auth-tabs"><button type="button" onClick={() => { setMode('login'); setError(''); }} className={mode === 'login' ? 'auth-tab-active' : ''}>Sign in</button><button type="button" onClick={() => { setMode('register'); setError(''); }} className={mode === 'register' ? 'auth-tab-active' : ''}>Create account</button></div>
          <form onSubmit={submit} className="auth-form">
            <label className="form-label">Email address<input className="input" type="text" inputMode="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" autoComplete="email" required /></label>
            <label className="form-label">Password<input className="input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === 'login' ? 'Enter your password' : 'Choose a password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={1} required /></label>
            {error && <div className="inline-error"><AlertCircle size={16} />{error}</div>}
            <button className="button button-primary auth-submit" disabled={busy}>{busy ? <LoaderCircle className="spinner" size={17} /> : <>{mode === 'login' ? 'Sign in to TaskFlow' : 'Create account'} <ArrowRight size={17} /></>}</button>
          </form>
          <div className="auth-trust"><ShieldCheck size={15} /><span>Secure session · JWT authentication</span></div>
          <p className="auth-api-note">Connected to your local TaskFlow API at <code>127.0.0.1:8000</code></p>
        </div>
      </section>
    </div>
  );
}

function WorkspaceWelcome({ onCreate }: { onCreate: () => void }) {
  return <div className="welcome-panel"><div className="welcome-orb"><Blocks size={30} /></div><div className="eyebrow">A FRESH START</div><h2>Create your first workspace</h2><p>A workspace keeps your projects, tasks, automations and team access together. You will become its owner automatically.</p><button className="button button-primary" onClick={onCreate}><Plus size={17} /> Create workspace</button></div>;
}

function OverviewPage({ projects, tasks, onNewProject, onNewTask, onOpenProject, onOpenTasks }: {
  projects: Project[]; tasks: Task[]; onNewProject: () => void; onNewTask: () => void; onOpenProject: (id: number) => void; onOpenTasks: () => void;
}) {
  const completed = tasks.filter((task) => task.status === 'done').length;
  const inProgress = tasks.filter((task) => task.status === 'in_progress').length;
  const todo = tasks.filter((task) => task.status === 'todo').length;
  const overdue = tasks.filter(isOverdue).length;
  const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
  const recentTasks = [...tasks].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 5);
  return (
    <div className="page-stack">
      <section className="welcome-banner">
        <div className="welcome-banner-copy"><div className="banner-tag"><Sparkles size={13} /> WORKSPACE SNAPSHOT</div><h2>Make progress visible.</h2><p>Build momentum with a clear view of work in motion and what needs your attention.</p><div className="banner-actions"><button className="button button-light" onClick={onNewProject}><Plus size={16} /> New project</button><button className="button button-glass" onClick={onOpenTasks}>View task board <ArrowRight size={16} /></button></div></div>
        <div className="banner-art" aria-hidden="true"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-spark spark-one">✳</div><div className="art-spark spark-two">✦</div><div className="art-card art-card-main"><div className="art-card-head"><span>Weekly momentum</span><ArrowUpRight size={16} /></div><div className="art-card-score">{progress}<small>%</small></div><div className="art-score-caption">of all tasks completed</div><div className="art-mini-bars">{[35, 54, 44, 72, 62, 88, 70].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div></div><div className="art-floating-pill"><span className="pill-check"><Check size={12} /></span> Moving forward</div></div>
      </section>

      <section className="metric-grid">
        <MetricCard label="Total projects" value={projects.length} note="Across this workspace" icon={FolderKanban} tone="lavender" trend="Workspace" />
        <MetricCard label="Open tasks" value={todo + inProgress} note={`${inProgress} currently in progress`} icon={ListTodo} tone="blue" trend="In motion" />
        <MetricCard label="Completed" value={completed} note={`${progress}% of all tasks`} icon={CheckCheck} tone="green" trend="Progress" />
        <MetricCard label="Overdue" value={overdue} note={overdue ? 'Needs a closer look' : 'You are all caught up'} icon={Clock3} tone={overdue ? 'orange' : 'slate'} trend={overdue ? 'Attention' : 'On track'} />
      </section>

      <div className="content-grid content-grid-overview">
        <section className="panel project-overview-panel">
          <div className="panel-heading"><div><h3>Project pulse</h3><p>See what is moving across your workspace.</p></div><button className="text-button" onClick={() => { if (projects.length) onOpenProject(projects[0].id); else onNewProject(); }}>{projects.length ? 'Open board' : 'Create project'} <ArrowRight size={14} /></button></div>
          {projects.length === 0 ? <EmptyState icon={FolderKanban} title="No projects yet" text="Create a project to collect tasks, deadlines and progress in one place." actionLabel="Create a project" onAction={onNewProject} /> : <div className="project-pulse-list">{projects.slice(0, 5).map((project, index) => {
            const projectTasks = tasks.filter((task) => task.project_id === project.id);
            const done = projectTasks.filter((task) => task.status === 'done').length;
            const percent = projectTasks.length ? Math.round(done / projectTasks.length * 100) : 0;
            return <button className="project-pulse-row" key={project.id} onClick={() => onOpenProject(project.id)}><div className={`project-icon project-color-${index % 4}`}><FolderKanban size={17} /></div><div className="project-pulse-info"><div className="project-pulse-name"><strong>{project.title}</strong><span>{projectTasks.length} {projectTasks.length === 1 ? 'task' : 'tasks'}</span></div><div className="progress-track"><i style={{ width: `${percent}%` }} /></div></div><div className="project-pulse-percent">{percent}%</div><ArrowRight size={15} className="row-arrow" /></button>;
          })}</div>}
        </section>

        <section className="panel work-summary-panel">
          <div className="panel-heading"><div><h3>Work breakdown</h3><p>Tasks by current status.</p></div><button className="icon-button quiet" onClick={onOpenTasks} title="Open task board"><ArrowUpRight size={17} /></button></div>
          <div className="donut-wrap"><div className="donut-chart" style={{ background: `conic-gradient(#6458e8 0 ${tasks.length ? todo / tasks.length * 100 : 0}%, #3b9b87 ${tasks.length ? todo / tasks.length * 100 : 0}% ${tasks.length ? (todo + inProgress) / tasks.length * 100 : 0}%, #cbd1df ${tasks.length ? (todo + inProgress) / tasks.length * 100 : 0}% 100%)` }}><div className="donut-hole"><strong>{tasks.length}</strong><span>Total tasks</span></div></div></div>
          <div className="status-legend"><div><span className="legend-dot dot-todo" /><span>To do</span><strong>{todo}</strong></div><div><span className="legend-dot dot-progress" /><span>In progress</span><strong>{inProgress}</strong></div><div><span className="legend-dot dot-done" /><span>Done</span><strong>{completed}</strong></div></div>
          <div className="summary-footer"><span>Delivery rate</span><strong>{progress}%</strong><div className="summary-progress"><i style={{ width: `${progress}%` }} /></div></div>
        </section>
      </div>

      <section className="panel recent-panel">
        <div className="panel-heading"><div><h3>Recently updated tasks</h3><p>Latest activity from your project boards.</p></div><button className="text-button" onClick={onOpenTasks}>All tasks <ArrowRight size={14} /></button></div>
        {recentTasks.length === 0 ? <EmptyState icon={ListTodo} title="Nothing on the board yet" text="Create your first task and your progress will appear here." actionLabel="Create a task" onAction={projects.length ? onNewTask : onNewProject} /> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Task</th><th>Project</th><th>Status</th><th>Priority</th><th>Due date</th></tr></thead><tbody>{recentTasks.map((task) => <tr key={task.id}><td><div className="table-task-title"><span className={`task-status-marker marker-${task.status}`} /><strong>{task.title}</strong></div></td><td><span className="muted-cell">{task.projectTitle ?? 'Project'}</span></td><td><StatusBadge status={task.status} /></td><td><PriorityBadge priority={task.priority} /></td><td><span className={isOverdue(task) ? 'overdue-text' : 'muted-cell'}>{dateLabel(task.deadline)}</span></td></tr>)}</tbody></table></div>}
      </section>
    </div>
  );
}

function MetricCard({ label, value, note, icon: Icon, tone, trend }: { label: string; value: number; note: string; icon: typeof LayoutDashboard; tone: string; trend: string }) {
  return <div className="metric-card"><div className="metric-card-top"><div className={`metric-icon metric-${tone}`}><Icon size={19} /></div><span className="metric-trend">{trend}</span></div><div className="metric-value">{value.toLocaleString()}</div><div className="metric-label">{label}</div><div className="metric-note">{note}</div></div>;
}

function ProjectsPage({ projects, tasks, onCreate, onEdit, onDelete, onOpen }: { projects: Project[]; tasks: Task[]; onCreate: () => void; onEdit: (project: Project) => void; onDelete: (project: Project) => void; onOpen: (id: number) => void }) {
  if (!projects.length) return <div className="panel empty-panel"><EmptyState icon={FolderKanban} title="Your next big thing starts here" text="Create a project, add tasks, set priorities and track delivery from one board." actionLabel="Create project" onAction={onCreate} /></div>;
  return <div className="project-card-grid">{projects.map((project, index) => {
    const projectTasks = tasks.filter((task) => task.project_id === project.id);
    const done = projectTasks.filter((task) => task.status === 'done').length;
    const inProgress = projectTasks.filter((task) => task.status === 'in_progress').length;
    const percent = projectTasks.length ? Math.round(done / projectTasks.length * 100) : 0;
    const priorities = projectTasks.filter((task) => task.priority === 'high' && task.status !== 'done').length;
    return <article className="project-card" key={project.id}>
      <div className="project-card-top"><div className={`project-icon project-icon-large project-color-${index % 4}`}><FolderKanban size={21} /></div><button className="icon-button quiet" onClick={() => onEdit(project)} title="Edit project"><Pencil size={16} /></button></div>
      <button className="project-card-title-button" onClick={() => onOpen(project.id)}><h3>{project.title}</h3><ArrowUpRight size={17} /></button>
      <p className="project-card-description">{project.description || 'No description added yet.'}</p>
      <div className="project-card-meta"><span><ListTodo size={14} /> {projectTasks.length} tasks</span><span><Clock3 size={14} /> {inProgress} in progress</span></div>
      <div className="project-card-progress-label"><span>Completion</span><strong>{percent}%</strong></div><div className="progress-track project-card-progress"><i style={{ width: `${percent}%` }} /></div>
      <div className="project-card-bottom"><span className="tiny-avatar-stack"><i>{initials(project.title).slice(0, 1)}</i><i>{initials(project.title).slice(-1)}</i></span><span className="project-card-bottom-text">{done}/{projectTasks.length} complete</span>{priorities > 0 && <span className="high-priority-count"><CircleAlert size={13} /> {priorities} high</span>}<button className="icon-button quiet delete-inline" onClick={() => onDelete(project)} aria-label="Delete project" title="Delete project"><Trash2 size={15} /></button></div>
    </article>;
  })}<button className="project-create-card" onClick={onCreate}><span className="create-circle"><Plus size={22} /></span><strong>Create a project</strong><span>Start with a clear goal and build from there.</span></button></div>;
}

function TasksPage({ tasks, projects, searchQuery, statusFilter, priorityFilter, projectFilter, setStatusFilter, setPriorityFilter, setProjectFilter, onEdit, onComplete, onDelete, onMove, onCreate, onCreateProject }: {
  tasks: Task[]; projects: Project[]; searchQuery: string; statusFilter: TaskStatus | 'all'; priorityFilter: TaskPriority | 'all'; projectFilter: number | 'all';
  setStatusFilter: (status: TaskStatus | 'all') => void; setPriorityFilter: (priority: TaskPriority | 'all') => void; setProjectFilter: (project: number | 'all') => void;
  onEdit: (task: Task) => void; onComplete: (task: Task) => void; onDelete: (task: Task) => void; onMove: (task: Task, status: TaskStatus) => void; onCreate: () => void; onCreateProject: () => void;
}) {
  const filtered = tasks.filter((task) => {
    const query = searchQuery.trim().toLowerCase();
    return (!query || `${task.title} ${task.description} ${task.projectTitle ?? ''}`.toLowerCase().includes(query))
      && (statusFilter === 'all' || task.status === statusFilter)
      && (priorityFilter === 'all' || task.priority === priorityFilter)
      && (projectFilter === 'all' || task.project_id === projectFilter);
  });
  const columns: TaskStatus[] = ['todo', 'in_progress', 'done'];
  if (!projects.length) return <div className="panel empty-panel"><EmptyState icon={FolderKanban} title="Create a project first" text="Tasks live inside projects. Create a project, then add and organize its tasks." actionLabel="Create a project" onAction={onCreateProject} /></div>;
  return <div className="board-wrap">
    <div className="board-toolbar"><div className="board-toolbar-left"><div className="board-mode-chip"><Blocks size={15} /> Board view</div><span className="board-total">{filtered.length} tasks</span></div><div className="board-filters"><label className="filter-select"><Filter size={14} /><select aria-label="Filter by project" value={projectFilter} onChange={(event) => setProjectFilter(event.target.value === 'all' ? 'all' : Number(event.target.value))}><option value="all">All projects</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select><ChevronDown size={13} /></label><label className="filter-select"><select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as TaskStatus | 'all')}><option value="all">All statuses</option><option value="todo">To do</option><option value="in_progress">In progress</option><option value="done">Done</option></select><ChevronDown size={13} /></label><label className="filter-select"><select aria-label="Filter by priority" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value as TaskPriority | 'all')}><option value="all">All priorities</option><option value="high">High priority</option><option value="medium">Medium priority</option><option value="low">Low priority</option></select><ChevronDown size={13} /></label></div></div>
    <div className="kanban-grid">{columns.map((status) => {
      const items = filtered.filter((task) => task.status === status);
      return <section className={`kanban-column column-${status}`} key={status}><header className="kanban-column-heading"><div className="kanban-title-wrap"><span className={`column-dot dot-${status}`} /><h3>{STATUS_LABEL[status]}</h3><span className="column-count">{items.length}</span></div><button className="icon-button quiet" onClick={onCreate} title="Add task"><Plus size={17} /></button></header><div className="kanban-cards">{items.map((task) => <TaskCard key={task.id} task={task} onEdit={() => onEdit(task)} onComplete={() => onComplete(task)} onDelete={() => onDelete(task)} onMove={(next) => onMove(task, next)} />)}{items.length === 0 && <div className="column-empty">No tasks here yet.</div>}</div>{status === 'todo' && <button className="column-add-task" onClick={onCreate}><Plus size={15} /> Add a task</button>}</section>;
    })}</div>
  </div>;
}

function TaskCard({ task, onEdit, onComplete, onDelete, onMove }: { task: Task; onEdit: () => void; onComplete: () => void; onDelete: () => void; onMove: (status: TaskStatus) => void }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return <article className="task-card"><div className="task-card-top"><PriorityBadge priority={task.priority} /><div className="task-more-wrap"><button className="icon-button tiny-icon-button" onClick={() => setMenuOpen((value) => !value)} aria-label="Task actions"><MoreHorizontal size={17} /></button>{menuOpen && <><button className="menu-dismiss" aria-label="Close action menu" onClick={() => setMenuOpen(false)} /><div className="task-action-menu"><button onClick={() => { setMenuOpen(false); onEdit(); }}><Pencil size={14} /> Edit task</button>{task.status !== 'todo' && <button onClick={() => { setMenuOpen(false); onMove('todo'); }}><CircleDashed size={14} /> Move to To do</button>}{task.status !== 'in_progress' && <button onClick={() => { setMenuOpen(false); onMove('in_progress'); }}><Clock3 size={14} /> Move to In progress</button>}{task.status !== 'done' && <button onClick={() => { setMenuOpen(false); onComplete(); }}><CheckCircleIcon /> Complete</button>}<button className="menu-danger" onClick={() => { setMenuOpen(false); onDelete(); }}><Trash2 size={14} /> Delete task</button></div></>}</div></div><button className="task-card-title" onClick={onEdit}>{task.title}</button>{task.description && <p className="task-card-description">{task.description}</p>}<div className="task-card-project"><span className="project-mini-dot" />{task.projectTitle ?? 'Project'}</div><div className="task-card-bottom"><span className={`task-due ${isOverdue(task) ? 'task-due-overdue' : ''}`}><CalendarDays size={13} />{dateLabel(task.deadline)}</span><div className="task-card-footer-right">{task.assignee_id !== null && <span className="assignee-chip" title={`Assignee ID ${task.assignee_id}`}>ID {task.assignee_id}</span>}{task.status !== 'done' && <button className="task-complete-button" onClick={onComplete} title="Mark complete"><Check size={14} /></button>}</div></div></article>;
}

function CheckCircleIcon() { return <CheckCheck size={14} />; }

function AutomationsPage({ items, onCreate, onEdit, onDelete, onToggle }: { items: Automation[]; onCreate: () => void; onEdit: (item: Automation) => void; onDelete: (item: Automation) => void; onToggle: (item: Automation) => void }) {
  return <div className="page-stack"><section className="automation-intro"><div className="automation-intro-icon"><Zap size={22} /></div><div><h3>When something happens, TaskFlow takes action.</h3><p>Current engine supports the <code>task.completed</code> trigger, an optional priority condition, and notifications to workspace members.</p></div><div className="automation-flow"><span>WHEN</span><ArrowRight size={15} /><span>IF</span><ArrowRight size={15} /><span>DO</span></div></section>
    {items.length === 0 ? <div className="panel empty-panel"><EmptyState icon={Workflow} title="No automations yet" text="Create a rule that sends a notification when a task is completed. You can optionally limit it to a specific priority." actionLabel="Create automation" onAction={onCreate} /></div> : <div className="automation-list">{items.map((item) => <article className={`automation-card ${!item.is_active ? 'automation-inactive' : ''}`} key={item.id}><div className="automation-card-icon"><Workflow size={19} /></div><div className="automation-card-main"><div className="automation-title-row"><h3>{item.name}</h3><span className={`state-pill ${item.is_active ? 'state-active' : 'state-paused'}`}><i />{item.is_active ? 'Active' : 'Paused'}</span></div><div className="automation-rule"><span className="rule-chip rule-when">WHEN</span><span>Task is completed</span><span className="rule-divider">·</span><span className="rule-chip rule-if">IF</span><span>{item.condition ? `Priority is ${item.condition.value}` : 'Any priority'}</span><span className="rule-divider">·</span><span className="rule-chip rule-do">DO</span><span>Notify workspace members</span></div><div className="automation-card-meta">Created {dateLabel(item.created_at)} <span>·</span> Rule #{item.id}</div></div><div className="automation-card-actions"><button className="button button-ghost button-small" onClick={() => onEdit(item)}><Pencil size={14} /> Edit</button><button className="toggle-switch" data-active={item.is_active} onClick={() => onToggle(item)} aria-label={item.is_active ? 'Pause automation' : 'Activate automation'}><span /></button><button className="icon-button quiet" onClick={() => onDelete(item)} title="Delete automation"><Trash2 size={15} /></button></div></article>)}</div>}
  </div>;
}

function WebhooksPage({ items, onCreate, onEdit, onDelete, onToggle }: { items: Webhook[]; onCreate: () => void; onEdit: (item: Webhook) => void; onDelete: (item: Webhook) => void; onToggle: (item: Webhook) => void }) {
  return <div className="page-stack"><section className="webhook-intro"><div className="webhook-intro-icon"><Globe size={22} /></div><div><h3>Connect TaskFlow to the rest of your stack.</h3><p>Subscribed endpoints receive signed-by-context event payloads through the Celery worker. Webhook URLs must use HTTPS and resolve to public IP addresses.</p></div><div className="event-total"><strong>{items.length.toString().padStart(2, '0')}</strong><span>ENDPOINTS</span></div></section>
    {items.length === 0 ? <div className="panel empty-panel"><EmptyState icon={WebhookIcon} title="No endpoints connected" text="Add a public HTTPS endpoint to receive project and task events from this workspace." actionLabel="Add a webhook" onAction={onCreate} /></div> : <div className="webhook-list">{items.map((item) => <article className="webhook-card" key={item.id}><div className="webhook-card-icon"><Link2 size={20} /></div><div className="webhook-card-main"><div className="webhook-url-row"><h3>{item.url}</h3><span className={`state-pill ${item.is_active ? 'state-active' : 'state-paused'}`}><i />{item.is_active ? 'Active' : 'Paused'}</span></div><div className="webhook-events"><span className="events-label">EVENTS</span>{item.events.map((event) => <code key={event}>{event}</code>)}</div><div className="webhook-meta">Added {dateLabel(item.created_at)} <span>·</span> Endpoint #{item.id}</div></div><div className="webhook-actions"><button className="icon-button quiet" onClick={() => onEdit(item)} title="Edit webhook"><Pencil size={15} /></button><button className="toggle-switch" data-active={item.is_active} onClick={() => onToggle(item)} aria-label={item.is_active ? 'Pause webhook' : 'Activate webhook'}><span /></button><button className="icon-button quiet" onClick={() => onDelete(item)} title="Delete webhook"><Trash2 size={15} /></button></div></article>)}</div>}
    <div className="info-note"><AlertCircle size={16} /><span>Delivery attempts and retry history are stored by the backend, but the current API does not expose a read endpoint for webhook deliveries yet.</span></div>
  </div>;
}

function ActivityPage({ items }: { items: AuditLog[] }) {
  if (!items.length) return <div className="panel empty-panel"><EmptyState icon={FileClock} title="The timeline is quiet" text="Project and task changes will appear here as audit events are written by the backend." /></div>;
  return <section className="panel activity-panel"><div className="panel-heading"><div><h3>Workspace timeline</h3><p>{items.length} recorded events</p></div><span className="subtle-chip"><ShieldCheck size={14} /> Audit trail</span></div><div className="activity-list">{items.map((item, index) => <div className="activity-row" key={item.id}><div className={`activity-icon activity-tone-${index % 4}`}>{item.entity_type === 'project' ? <FolderKanban size={16} /> : item.action.includes('completed') ? <CheckCheck size={16} /> : <ListTodo size={16} />}</div><div className="activity-copy"><strong>{humanizeAction(item.action)}</strong><span>{item.entity_type} <b>#{item.entity_id}</b> in workspace #{item.workspace_id}</span><small>Performed by user #{item.user_id}</small></div><time>{timeLabel(item.created_at)}</time></div>)}</div></section>;
}

function NotificationsPage({ items }: { items: Notification[] }) {
  if (!items.length) return <div className="panel empty-panel"><EmptyState icon={Bell} title="You are all caught up" text="Notifications from TaskFlow automations will appear here. There is nothing that needs your attention right now." /></div>;
  return <section className="panel notification-panel"><div className="panel-heading"><div><h3>Inbox</h3><p>{items.filter((item) => !item.is_read).length} unread · {items.length} total</p></div><span className="subtle-chip"><Bell size={14} /> Workspace updates</span></div><div className="notification-list">{items.map((item) => <article className={`notification-row ${!item.is_read ? 'notification-unread' : ''}`} key={item.id}><div className="notification-icon"><Sparkles size={17} /></div><div className="notification-copy"><strong>{item.message}</strong><span>Task #{item.task_id} · Workspace #{item.workspace_id}</span><small>{timeLabel(item.created_at)}</small></div>{!item.is_read && <span className="unread-dot" title="Unread" />}</article>)}</div><div className="info-note"><AlertCircle size={16} /><span>The backend currently exposes notification listing only; a mark-as-read endpoint has not been added yet.</span></div></section>;
}

function TeamPage({ workspaceId, onSuccess }: { workspaceId: number; onSuccess: (message: string) => void }) {
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState<Role>('member');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [actionRole, setActionRole] = useState<Role>('member');
  const [actionUserId, setActionUserId] = useState('');
  const submitAdd = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true); setNotice('');
    try {
      await api(`/workspaces/${workspaceId}/members`, { method: 'POST', body: jsonBody({ user_id: Number(userId), role }) });
      setNotice('Member added successfully.'); setUserId(''); onSuccess('Member added to workspace.');
    } catch (error) { setNotice(getErrorMessage(error)); }
    finally { setBusy(false); }
  };
  const applyRole = async () => {
    if (!actionUserId) return;
    setBusy(true); setNotice('');
    try {
      await api(`/workspaces/${workspaceId}/members/${Number(actionUserId)}/role`, { method: 'PATCH', body: jsonBody({ role: actionRole }) });
      setNotice('Member role updated.'); onSuccess('Member role updated.');
    } catch (error) { setNotice(getErrorMessage(error)); }
    finally { setBusy(false); }
  };
  const removeMember = async () => {
    if (!actionUserId || !window.confirm(`Remove user #${actionUserId} from this workspace?`)) return;
    setBusy(true); setNotice('');
    try {
      await api(`/workspaces/${workspaceId}/members/${Number(actionUserId)}`, { method: 'DELETE' });
      setNotice('Member removed.'); onSuccess('Member removed from workspace.'); setActionUserId('');
    } catch (error) { setNotice(getErrorMessage(error)); }
    finally { setBusy(false); }
  };
  return <div className="team-layout"><section className="panel team-panel"><div className="panel-heading"><div><h3>Add a workspace member</h3><p>Invite an existing TaskFlow user using their numeric user ID.</p></div><div className="team-panel-icon"><Users size={19} /></div></div><form className="team-form" onSubmit={submitAdd}><label className="form-label">User ID<input className="input" inputMode="numeric" type="number" min="1" value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="e.g. 12" required /></label><label className="form-label">Workspace role<select className="input" value={role} onChange={(event) => setRole(event.target.value as Role)}><option value="admin">Admin</option><option value="member">Member</option><option value="viewer">Viewer</option><option value="owner">Owner</option></select></label><button className="button button-primary" disabled={busy}><Plus size={16} /> Add member</button></form><div className="role-key"><div><strong>Owner</strong><span>Full workspace control</span></div><div><strong>Admin</strong><span>Can manage members</span></div><div><strong>Member</strong><span>Can create and edit</span></div><div><strong>Viewer</strong><span>Read-only access</span></div></div></section>
    <section className="panel team-panel"><div className="panel-heading"><div><h3>Manage access</h3><p>Change a known user's role or remove them.</p></div><div className="team-panel-icon"><ShieldCheck size={19} /></div></div><div className="team-form team-form-manage"><label className="form-label">User ID<input className="input" inputMode="numeric" type="number" min="1" value={actionUserId} onChange={(event) => setActionUserId(event.target.value)} placeholder="e.g. 12" /></label><label className="form-label">New role<select className="input" value={actionRole} onChange={(event) => setActionRole(event.target.value as Role)}><option value="admin">Admin</option><option value="member">Member</option><option value="viewer">Viewer</option><option value="owner">Owner</option></select></label><button className="button button-secondary" onClick={applyRole} disabled={busy || !actionUserId}>Update role</button><button className="button button-danger-soft" onClick={removeMember} disabled={busy || !actionUserId}><Trash2 size={15} /> Remove</button></div>{notice && <div className="inline-status"><AlertCircle size={15} />{notice}</div>}</section>
    <div className="info-note team-note"><AlertCircle size={16} /><span>The current backend has endpoints to add, change and remove members, but it does not yet expose <code>GET /workspaces/{'{workspace_id}'}/members</code>. Until that endpoint exists, this screen cannot display a full member roster; manage members by user ID.</span></div>
  </div>;
}

function ProjectModal({ existing, onClose, onSave }: { existing?: Project; onClose: () => void; onSave: (value: { title: string; description: string }) => Promise<void> }) {
  const [title, setTitle] = useState(existing?.title ?? '');
  const [description, setDescription] = useState(existing?.description ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { await onSave({ title: title.trim(), description: description.trim() }); } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); } };
  return <ModalShell title={existing ? 'Edit project' : 'Create a project'} subtitle="Give the work a clear name and a little context." onClose={onClose}><form className="modal-form" onSubmit={submit}><label className="form-label">Project name<input className="input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Website relaunch" maxLength={100} required autoFocus /></label><label className="form-label">Description<textarea className="input textarea" rows={4} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What does success look like?" maxLength={1000} required /></label>{error && <div className="inline-error"><AlertCircle size={15} />{error}</div>}<ModalActions busy={busy} submitLabel={existing ? 'Save changes' : 'Create project'} onCancel={onClose} /></form></ModalShell>;
}

function WorkspaceModal({ onClose, onSave }: { onClose: () => void; onSave: (name: string) => Promise<void> }) {
  const [name, setName] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const submit = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { await onSave(name.trim()); } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); } };
  return <ModalShell title="Create a workspace" subtitle="Your workspace is the home for projects, tasks, rules and activity." onClose={onClose}><form className="modal-form" onSubmit={submit}><label className="form-label">Workspace name<input className="input" value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Product team" maxLength={100} required autoFocus /></label><div className="info-note"><ShieldCheck size={15} /><span>You will automatically be assigned the owner role.</span></div>{error && <div className="inline-error"><AlertCircle size={15} />{error}</div>}<ModalActions busy={busy} submitLabel="Create workspace" onCancel={onClose} /></form></ModalShell>;
}

function TaskModal({ existing, projects, defaultProjectId, onClose, onSave }: { existing?: Task; projects: Project[]; defaultProjectId: number | null; onClose: () => void; onSave: (value: { title: string; description: string; status: TaskStatus; priority: TaskPriority; project_id: number; deadline: string | null; assignee_id: number | null }) => Promise<void> }) {
  const [title, setTitle] = useState(existing?.title ?? '');
  const [description, setDescription] = useState(existing?.description ?? '');
  const [projectId, setProjectId] = useState<number | ''>(existing?.project_id ?? defaultProjectId ?? projects[0]?.id ?? '');
  const [status, setStatus] = useState<TaskStatus>(existing?.status ?? 'todo');
  const [priority, setPriority] = useState<TaskPriority>(existing?.priority ?? 'medium');
  const [deadline, setDeadline] = useState(existing?.deadline ? new Date(existing.deadline).toISOString().slice(0, 16) : '');
  const [assigneeId, setAssigneeId] = useState(existing?.assignee_id?.toString() ?? '');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!projectId) { setError('Choose a project first.'); return; }
    setBusy(true); setError('');
    try { await onSave({ title: title.trim(), description: description.trim(), status, priority, project_id: Number(projectId), deadline: deadline ? new Date(deadline).toISOString() : null, assignee_id: assigneeId.trim() ? Number(assigneeId) : null }); }
    catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); }
  };
  return <ModalShell title={existing ? 'Edit task' : 'Create a task'} subtitle="Keep the next action clear and easy to track." onClose={onClose}><form className="modal-form" onSubmit={submit}><label className="form-label">Task title<input className="input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What needs to get done?" maxLength={100} required autoFocus /></label><label className="form-label">Description<textarea className="input textarea" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Add useful context for the team." maxLength={1000} required /></label><div className="form-grid-2"><label className="form-label">Project<select className="input" value={projectId} onChange={(event) => setProjectId(event.target.value ? Number(event.target.value) : '')} required disabled={Boolean(existing)}><option value="" disabled>Select project</option>{projects.map((project) => <option value={project.id} key={project.id}>{project.title}</option>)}</select></label><label className="form-label">Status<select className="input" value={status} onChange={(event) => setStatus(event.target.value as TaskStatus)}><option value="todo">To do</option><option value="in_progress">In progress</option><option value="done">Done</option></select></label><label className="form-label">Priority<select className="input" value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label><label className="form-label">Deadline<input className="input" type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label><label className="form-label form-grid-full">Assignee user ID <span className="optional-label">optional</span><input className="input" type="number" min="1" value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)} placeholder="Leave blank for unassigned" /></label></div>{error && <div className="inline-error"><AlertCircle size={15} />{error}</div>}<ModalActions busy={busy} submitLabel={existing ? 'Save changes' : 'Create task'} onCancel={onClose} /></form></ModalShell>;
}

function AutomationModal({ existing, onClose, onSave }: { existing?: Automation; onClose: () => void; onSave: (value: { name: string; condition: { field: 'priority'; operator: 'eq'; value: TaskPriority } | null; is_active: boolean }) => Promise<void> }) {
  const [name, setName] = useState(existing?.name ?? '');
  const [priority, setPriority] = useState<TaskPriority | 'any'>(existing?.condition?.value ?? 'any');
  const [active, setActive] = useState(existing?.is_active ?? true);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const submit = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { await onSave({ name: name.trim(), condition: priority === 'any' ? null : { field: 'priority', operator: 'eq', value: priority }, is_active: active }); } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); } };
  return <ModalShell title={existing ? 'Edit automation' : 'New automation'} subtitle="Configure the rule supported by the current TaskFlow engine." onClose={onClose}><form className="modal-form" onSubmit={submit}><label className="form-label">Rule name<input className="input" value={name} onChange={(event) => setName(event.target.value)} maxLength={100} placeholder="e.g. Notify the team on high-priority completion" required autoFocus /></label><div className="rule-builder"><div className="rule-builder-step"><span className="rule-step-label rule-when">WHEN</span><div><strong>Task is completed</strong><small>Trigger event · task.completed</small></div></div><div className="rule-builder-connector" /><div className="rule-builder-step"><span className="rule-step-label rule-if">IF</span><div><strong>Priority matches</strong><small>Optional condition</small></div><select className="input" value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority | 'any')}><option value="any">Any priority</option><option value="high">High priority</option><option value="medium">Medium priority</option><option value="low">Low priority</option></select></div><div className="rule-builder-connector" /><div className="rule-builder-step"><span className="rule-step-label rule-do">DO</span><div><strong>Send a notification</strong><small>To all workspace members</small></div></div></div><label className="checkbox-row"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /><span className="checkbox-visual"><Check size={12} /></span><span><strong>Enable this automation</strong><small>Active rules run when matching tasks are completed.</small></span></label>{error && <div className="inline-error"><AlertCircle size={15} />{error}</div>}<ModalActions busy={busy} submitLabel={existing ? 'Save rule' : 'Create rule'} onCancel={onClose} /></form></ModalShell>;
}

function WebhookModal({ existing, onClose, onSave }: { existing?: Webhook; onClose: () => void; onSave: (value: { url: string; events: WebhookEvent[]; is_active: boolean }) => Promise<void> }) {
  const [url, setUrl] = useState(existing?.url ?? 'https://');
  const [events, setEvents] = useState<WebhookEvent[]>(existing?.events ?? ['task.completed']);
  const [active, setActive] = useState(existing?.is_active ?? true);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const toggleEvent = (event: WebhookEvent) => setEvents((current) => current.includes(event) ? current.filter((item) => item !== event) : [...current, event]);
  const submit = async (event: FormEvent) => { event.preventDefault(); if (!events.length) { setError('Select at least one event.'); return; } setBusy(true); setError(''); try { await onSave({ url: url.trim(), events, is_active: active }); } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); } };
  return <ModalShell title={existing ? 'Edit webhook' : 'Add a webhook'} subtitle="Subscribe a public HTTPS endpoint to TaskFlow events." onClose={onClose}><form className="modal-form" onSubmit={submit}><label className="form-label">Endpoint URL<input className="input" type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://api.example.com/events" required /></label><div className="form-label">Subscribe to events <span className="optional-label">Select at least one</span></div><div className="event-checkbox-grid">{WEBHOOK_EVENTS.map((event) => <label key={event} className={`event-checkbox ${events.includes(event) ? 'event-checkbox-active' : ''}`}><input type="checkbox" checked={events.includes(event)} onChange={() => toggleEvent(event)} /><span className="checkbox-visual"><Check size={12} /></span><code>{event}</code></label>)}</div>{existing ? <label className="checkbox-row"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /><span className="checkbox-visual"><Check size={12} /></span><span><strong>Enable this endpoint</strong><small>Paused endpoints are not queued for delivery.</small></span></label> : <div className="info-note"><ShieldCheck size={15} /><span>New endpoints are created active by the current API. TaskFlow requires HTTPS and rejects localhost, private and non-public destination IPs.</span></div>}<div className="info-note"><AlertCircle size={15} /><span>Webhook payload delivery runs in the background through the Celery worker.</span></div>{error && <div className="inline-error"><AlertCircle size={15} />{error}</div>}<ModalActions busy={busy} submitLabel={existing ? 'Save endpoint' : 'Add endpoint'} onCancel={onClose} /></form></ModalShell>;
}

function ModalShell({ title, subtitle, onClose, children }: { title: string; subtitle: string; onClose: () => void; children: ReactNode }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="modal-card" role="dialog" aria-modal="true" aria-label={title}><div className="modal-heading"><div><h2>{title}</h2><p>{subtitle}</p></div><button className="icon-button quiet" onClick={onClose} aria-label="Close dialog"><X size={18} /></button></div>{children}</section></div>;
}

function ModalActions({ busy, submitLabel, onCancel }: { busy: boolean; submitLabel: string; onCancel: () => void }) {
  return <div className="modal-actions"><button type="button" className="button button-ghost" onClick={onCancel} disabled={busy}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? <LoaderCircle className="spinner" size={16} /> : <>{submitLabel} <ArrowRight size={15} /></>}</button></div>;
}

function EmptyState({ icon: Icon, title, text, actionLabel, onAction }: { icon: typeof LayoutDashboard; title: string; text: string; actionLabel?: string; onAction?: () => void }) {
  return <div className="empty-state"><div className="empty-state-icon"><Icon size={23} /></div><h3>{title}</h3><p>{text}</p>{actionLabel && onAction && <button className="button button-primary button-small" onClick={onAction}><Plus size={15} />{actionLabel}</button>}</div>;
}

function PageLoading() {
  return <div className="page-loading"><LoaderCircle className="spinner" size={20} /><span>Loading workspace data...</span></div>;
}

function StatusBadge({ status }: { status: TaskStatus }) {
  return <span className={`status-badge status-${status}`}><i />{STATUS_LABEL[status]}</span>;
}

function PriorityBadge({ priority }: { priority: TaskPriority }) {
  return <span className={`priority-badge priority-${priority}`}><span className="priority-symbol">{priority === 'high' ? '↑' : priority === 'medium' ? '↗' : '↓'}</span>{PRIORITY_LABEL[priority]}</span>;
}

function Toast({ toast, onClose }: { toast: NonNullable<ToastState>; onClose: () => void }) {
  return <div className={`toast toast-${toast.kind}`} role="status"><span className="toast-icon">{toast.kind === 'success' ? <Check size={17} /> : toast.kind === 'error' ? <AlertCircle size={17} /> : <Activity size={17} />}</span><span>{toast.message}</span><button className="icon-button quiet" onClick={onClose} aria-label="Dismiss notification"><X size={15} /></button></div>;
}
