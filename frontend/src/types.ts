export type Role = 'owner' | 'admin' | 'member' | 'viewer';
export type TaskStatus = 'todo' | 'in_progress' | 'done';
export type TaskPriority = 'low' | 'medium' | 'high';

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Workspace {
  id: number;
  name: string;
  created_at: string;
}

export interface Project {
  id: number;
  workspace_id: number;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: number;
  project_id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  deadline: string | null;
  assignee_id: number | null;
  created_at: string;
  updated_at: string;
  projectTitle?: string;
}

export interface Automation {
  id: number;
  workspace_id: number;
  name: string;
  trigger: 'task.completed';
  condition: { field: 'priority'; operator: 'eq'; value: TaskPriority } | null;
  action: { type: 'send_notification'; recipients: 'workspace_members' };
  is_active: boolean;
  created_at: string;
}

export type WebhookEvent = 'task.created' | 'task.updated' | 'task.completed' | 'project.created';

export interface Webhook {
  id: number;
  workspace_id: number;
  url: string;
  events: WebhookEvent[];
  is_active: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  workspace_id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  created_at: string;
}

export interface Notification {
  id: number;
  user_id: number;
  workspace_id: number;
  task_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}

export type PageKey = 'overview' | 'projects' | 'tasks' | 'automations' | 'webhooks' | 'activity' | 'notifications' | 'team';
