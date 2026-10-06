// ===== 需求树节点状态 =====
export type NodeStatus = 'PENDING' | 'DESIGNING' | 'IMPLEMENTING' | 'PASSED' | 'FAILED';

// ===== 阶段 =====
export type Stage = 'DESIGN' | 'TEST' | 'IMPLEMENT';

// ===== 需求树节点 =====
export interface ReqNode {
  id: string;
  parent: string | null;
  name: string;
  desc: string;
  status: NodeStatus;
  stage: Stage;
  model: string;
  duration: number; // 秒，0 表示未完成
  cost: number; // 元
  failReason?: string;
}

export interface RequirementTree {
  title: string;
  nodes: ReqNode[];
}

// ===== 模型价格 =====
export interface ModelPrice {
  in: number; // 输入价格 / 百万 token
  out: number; // 输出价格 / 百万 token
}

// ===== 三个阶段选用的模型 =====
export type PhaseKey = 'interface' | 'testgen' | 'tdd';

export type ModelSelection = Record<PhaseKey, string>;

// ===== 阶段 token 预估（百万） =====
export interface PhaseTokens {
  in: number;
  out: number;
}

// ===== 日志行 =====
export type LogLevel = 'info' | 'success' | 'warn' | 'error' | 'system';

export interface LogLine {
  time: string;
  level: LogLevel;
  message: string;
}

// ===== 测试用例 =====
export type TestStatus = 'PASSED' | 'FAILED' | 'SKIPPED';

export interface TestCase {
  id: string;
  name: string;
  status: TestStatus;
  relatedReq: string;
  duration: number;
  failReason?: string;
}

// ===== 编译状态（全局） =====
export interface CompileState {
  running: boolean;
  progress: number; // 0-100
  phaseLabel: string;
  elapsedSec: number;
  cost: number;
  done: boolean;
}
