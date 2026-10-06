import axios from 'axios';
import type { LogLevel, NodeStatus, ReqNode, RequirementTree, Stage, TestCase } from '../types';

const baseURL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000';

export const http = axios.create({
  baseURL,
  timeout: 60000,
});

// ===== 后端响应类型 =====
export interface BackendTreeNode {
  id: string;
  parent: string | null;
  name: string;
  desc: string;
  status: string;
  stage: string;
}

export interface GenerateTreeResponse {
  title: string;
  nodes: BackendTreeNode[];
  source?: string;
  requirement_yaml?: string;
}

export interface CompilePayload {
  requirement_text: string;
  requirement_yaml?: string;
  app_type: string;
  models: { design: string; test: string; development: string };
  api_key: string;
  base_url: string;
  model?: string;
}

export interface StartCompileResponse {
  task_id: string;
  status: string;
  message?: string;
}

export interface BackendLog {
  timestamp: string;
  level: string;
  message: string;
}

export interface StatusResponse {
  task_id: string;
  status: string;
  progress: number;
  current_stage: string;
  current_node?: string;
  nodes: BackendTreeNode[];
  logs: BackendLog[];
  stats: {
    completed_nodes: number;
    total_nodes: number;
    elapsed_seconds: number;
    estimated_cost: number;
  };
}

export interface BackendTestResult {
  name: string;
  status: string;
  error?: string | null;
}

export interface ResultResponse {
  task_id: string;
  status: string;
  preview_url?: string | null;
  download_url?: string;
  test_results: BackendTestResult[];
  output_dir?: string;
  summary?: {
    total_nodes: number;
    passed_nodes: number;
    failed_nodes: number;
    total_time_seconds: number;
    total_cost: number;
  };
}

// ===== 映射工具 =====
/** 后端节点 status -> 前端 NodeStatus。RUNNING 根据 stage 映射为进行中 */
export function mapNodeStatus(bStatus: string, bStage: string): NodeStatus {
  const s = (bStatus || '').toUpperCase();
  if (s === 'PASSED' || s === 'SUCCESS' || s === 'SUCCESSFUL') return 'PASSED';
  if (s === 'FAILED' || s === 'FAILURE' || s === 'ERROR') return 'FAILED';
  if (s === 'RUNNING' || s === 'DOING' || s === 'IN_PROGRESS') {
    return bStage === 'DESIGN' ? 'DESIGNING' : 'IMPLEMENTING';
  }
  return 'PENDING';
}

/** 后端日志 level（大写）-> 前端 LogLevel（小写） */
export function mapLogLevel(bLevel: string): LogLevel {
  switch ((bLevel || '').toUpperCase()) {
    case 'SUCCESS':
      return 'success';
    case 'WARN':
    case 'WARNING':
      return 'warn';
    case 'ERROR':
    case 'ERR':
      return 'error';
    case 'SYSTEM':
      return 'system';
    default:
      return 'info';
  }
}

function mapStage(bStage: string): Stage {
  const s = (bStage || '').toUpperCase();
  if (s === 'DESIGN') return 'DESIGN';
  if (s === 'TEST') return 'TEST';
  return 'IMPLEMENT';
}

/** 后端节点数组 -> 前端 ReqNode[]（补默认值） */
export function mapNodes(bNodes: BackendTreeNode[]): ReqNode[] {
  return bNodes.map((n) => ({
    id: n.id,
    parent: n.parent,
    name: n.name,
    desc: n.desc,
    status: mapNodeStatus(n.status, n.stage),
    stage: mapStage(n.stage),
    model: '',
    duration: 0,
    cost: 0,
    failReason: undefined,
  }));
}

export function mapGenerateTree(resp: GenerateTreeResponse): RequirementTree {
  return {
    title: resp.title || '需求框架',
    nodes: mapNodes(resp.nodes || []),
  };
}

export function mapTests(bTests: BackendTestResult[]): TestCase[] {
  return bTests.map((t, i) => {
    const st = (t.status || '').toUpperCase();
    return {
      id: `TC-${String(i + 1).padStart(3, '0')}`,
      name: t.name,
      status: st === 'PASSED' || st === 'SUCCESS' ? 'PASSED' : st === 'FAILED' ? 'FAILED' : 'SKIPPED',
      relatedReq: '',
      duration: 0,
      failReason: t.error || undefined,
    };
  });
}

// ===== API 函数 =====
export async function generateTree(
  requirement: string,
  appType: string,
  apiKey?: string,
  baseUrl?: string,
): Promise<GenerateTreeResponse> {
  const { data } = await http.post<GenerateTreeResponse>('/api/generate-tree', {
    requirement,
    app_type: appType,
    ...(apiKey ? { api_key: apiKey } : {}),
    ...(baseUrl ? { base_url: baseUrl } : {}),
  });
  return data;
}

export async function startCompile(payload: CompilePayload): Promise<StartCompileResponse> {
  const { data } = await http.post<StartCompileResponse>('/api/compile', payload);
  return data;
}

export async function getStatus(taskId: string, since?: number): Promise<StatusResponse> {
  const { data } = await http.get<StatusResponse>(`/api/status/${taskId}`, {
    params: since ? { since } : {},
  });
  return data;
}

export async function getResult(taskId: string): Promise<ResultResponse> {
  const { data } = await http.get<ResultResponse>(`/api/result/${taskId}`);
  return data;
}

export async function cancelCompile(taskId: string): Promise<void> {
  await http.post(`/api/cancel/${taskId}`);
}

export interface ServerHistoryItem {
  task_id?: string;
  title?: string;
  app_type?: string;
  status?: string;
  created_at?: string;
  total_nodes?: number;
  passed_nodes?: number;
}

/** 拉取后端历史（失败时返回空数组，不抛错） */
export async function getServerHistory(): Promise<ServerHistoryItem[]> {
  try {
    const { data } = await http.get<ServerHistoryItem[] | { items?: ServerHistoryItem[] }>('/api/history', {
      timeout: 5000,
    });
    if (Array.isArray(data)) return data;
    return data.items ?? [];
  } catch {
    return [];
  }
}
