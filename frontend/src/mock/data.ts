import type {
  ModelPrice,
  ModelSelection,
  PhaseKey,
  PhaseTokens,
  RequirementTree,
  TestCase,
} from '../types';

// ===== 模型价格（元 / 百万 token）=====
export const MODEL_PRICES: Record<string, ModelPrice> = {
  'deepseek-v4-pro': { in: 9, out: 27 },
  'deepseek-v4-flash': { in: 1, out: 4 },
  'qwen3.7-plus': { in: 2, out: 8 },
  'glm-5.3-flash': { in: 0.8, out: 2.8 },
};

export const MODEL_OPTIONS = Object.keys(MODEL_PRICES);

export const DEFAULT_MODELS: ModelSelection = {
  interface: 'deepseek-v4-pro',
  testgen: 'qwen3.7-plus',
  tdd: 'deepseek-v4-flash',
};

// ===== 各阶段预估 token 用量（百万）=====
export const PHASE_TOKENS: Record<PhaseKey, PhaseTokens> = {
  interface: { in: 0.9, out: 0.85 },
  testgen: { in: 1.1, out: 1.0 },
  tdd: { in: 2.0, out: 1.93 },
};

export const PHASE_LABELS: Record<PhaseKey, { title: string; sub: string }> = {
  interface: { title: '需求设计阶段', sub: 'InterfaceDesigner' },
  testgen: { title: '测试生成阶段', sub: 'TestGenerator' },
  tdd: { title: '开发实现阶段', sub: 'TestDrivenDeveloper' },
};

/** 计算某个阶段使用某模型的预估成本 */
export function phaseCost(modelKey: string, phase: PhaseKey): number {
  const price = MODEL_PRICES[modelKey];
  const tok = PHASE_TOKENS[phase];
  if (!price || !tok) return 0;
  return price.in * tok.in + price.out * tok.out;
}

/** 当前三阶段配置总预估成本 */
export function totalCost(sel: ModelSelection): number {
  return phaseCost(sel.interface, 'interface') + phaseCost(sel.testgen, 'testgen') + phaseCost(sel.tdd, 'tdd');
}

/** 全用顶级模型（deepseek-v4-pro）的成本 */
export function allProCost(): number {
  return totalCost({ interface: 'deepseek-v4-pro', testgen: 'deepseek-v4-pro', tdd: 'deepseek-v4-pro' });
}

// ===== Mock 需求树：待办清单应用 =====
export function buildTodoTree(): RequirementTree {
  const n = (
    id: string,
    parent: string | null,
    name: string,
    desc: string,
    stage: 'DESIGN' | 'TEST' | 'IMPLEMENT',
    model: string,
    duration = 0,
    cost = 0,
    failReason = '',
  ) => ({
    id,
    parent,
    name,
    desc,
    status: 'PENDING' as const,
    stage,
    model,
    duration,
    cost,
    failReason,
  });

  return {
    title: '待办清单应用',
    nodes: [
      n('REQ-1', null, '待办清单应用', '支持添加、完成、删除、按日期筛选的待办清单整体需求包。', 'DESIGN', 'deepseek-v4-pro'),
      n('REQ-1-1', 'REQ-1', '任务核心管理', '任务的创建、编辑、完成与删除。', 'DESIGN', 'deepseek-v4-pro'),
      n('REQ-1-1-1', 'REQ-1-1', '添加任务', '输入任务标题即可新增一条待办。', 'IMPLEMENT', 'deepseek-v4-flash'),
      n('REQ-1-1-2', 'REQ-1-1', '打勾完成任务', '点击复选框标记任务为已完成。', 'IMPLEMENT', 'deepseek-v4-flash'),
      n('REQ-1-1-3', 'REQ-1-1', '删除任务', '滑出或按钮删除单条任务。', 'IMPLEMENT', 'glm-5.3-flash'),
      n('REQ-1-2', 'REQ-1', '日期与筛选', '按截止日期筛选与排序任务。', 'DESIGN', 'deepseek-v4-pro'),
      n('REQ-1-2-1', 'REQ-1-2', '设置截止日期', '为任务选择日期。', 'IMPLEMENT', 'qwen3.7-plus'),
      n('REQ-1-2-2', 'REQ-1-2', '按日期筛选', '全部 / 今天 / 已过期 筛选。', 'IMPLEMENT', 'qwen3.7-plus'),
      n('REQ-1-3', 'REQ-1', '数据持久化', '任务保存到本地存储，刷新不丢失。', 'DESIGN', 'deepseek-v4-pro'),
      n('REQ-1-3-1', 'REQ-1-3', '本地存储读写', 'localStorage 持久化任务列表。', 'IMPLEMENT', 'deepseek-v4-flash'),
      n('REQ-1-4', 'REQ-1', '界面与交互', '简洁的列表布局与空状态提示。', 'TEST', 'qwen3.7-plus'),
      n('REQ-1-4-1', 'REQ-1-4', '空状态引导', '无任务时显示提示文案。', 'TEST', 'qwen3.7-plus'),
    ],
  };
}

// ===== Mock 需求树：语音日历（演示模式专用）=====
const VC_MODEL = { design: 'deepseek-v4-pro', impl: 'deepseek-v4-flash' };

export function buildVoiceCalendarTree(): RequirementTree {
  const n = (
    id: string,
    parent: string | null,
    name: string,
    desc: string,
    stage: 'DESIGN' | 'IMPLEMENT',
  ) => ({
    id,
    parent,
    name,
    desc,
    status: 'PENDING' as const,
    stage,
    model: stage === 'DESIGN' ? VC_MODEL.design : VC_MODEL.impl,
    duration: 0,
    cost: 0,
    failReason: '',
  });

  return {
    title: '语音日历应用',
    nodes: [
      n('REQ-1', null, '用户系统', '注册、登录与路由鉴权，保障账户安全。', 'DESIGN'),
      n('REQ-1-1', 'REQ-1', '用户注册', '手机号注册、密码加密存储、发送验证码。', 'IMPLEMENT'),
      n('REQ-1-2', 'REQ-1', '用户登录', '账号密码登录，签发 JWT Token 鉴权。', 'IMPLEMENT'),
      n('REQ-1-3', 'REQ-1', '路由守卫', '未登录用户自动跳转登录页。', 'IMPLEMENT'),
      n('REQ-2', null, '日历日程管理', '月视图展示与日程的增删改查。', 'DESIGN'),
      n('REQ-2-1', 'REQ-2', '月视图日历展示', '公历月历网格，当天高亮，月份切换。', 'IMPLEMENT'),
      n('REQ-2-2', 'REQ-2', '日程增删改查', '新建、编辑、删除、查询日程。', 'IMPLEMENT'),
      n('REQ-2-3', 'REQ-2', '日程分类标签', '为日程添加颜色分类标签。', 'IMPLEMENT'),
      n('REQ-3', null, '语音交互', '语音录入、自然语言解析与指令执行。', 'DESIGN'),
      n('REQ-3-1', 'REQ-3', '语音录入', '调用百度ASR语音识别API，将语音转为文字。', 'IMPLEMENT'),
      n('REQ-3-2', 'REQ-3', '自然语言解析', '豆包NLP解析"明天下午三点开会"等口语。', 'IMPLEMENT'),
      n('REQ-3-3', 'REQ-3', '语音指令执行', '解析结果自动创建对应日程。', 'IMPLEMENT'),
      n('REQ-4', null, '提醒通知', '日程到期提醒与多渠道通知。', 'DESIGN'),
      n('REQ-4-1', 'REQ-4', '定时提醒推送', '日程到期前推送站内/系统通知。', 'IMPLEMENT'),
      n('REQ-4-2', 'REQ-4', '短信通知', '重要日程通过短信通道发送提醒。', 'IMPLEMENT'),
      n('REQ-5', null, '系统集成', '前后端联调与数据库设计。', 'DESIGN'),
      n('REQ-5-1', 'REQ-5', '前后端联调', 'Vue3前端与SpringBoot后端联调，API前缀/api，端口8888。', 'IMPLEMENT'),
      n('REQ-5-2', 'REQ-5', '数据库设计', 'User 与 Schedule 表结构及外键设计。', 'IMPLEMENT'),
    ],
  };
}

// 演示模式固定失败节点
export const DEMO_FAILED_NODES = ['REQ-4-2', 'REQ-2-3', 'REQ-5-2'];

// ===== Mock 需求树：移动待办 APP =====
export function buildMobileTodoTree(): RequirementTree {
  const n = (
    id: string,
    parent: string | null,
    name: string,
    desc: string,
    stage: 'DESIGN' | 'TEST' | 'IMPLEMENT',
  ) => ({
    id,
    parent,
    name,
    desc,
    status: 'PENDING' as const,
    stage,
    model: '',
    duration: 0,
    cost: 0,
    failReason: '',
  });

  return {
    title: '移动待办 APP',
    nodes: [
      n('REQ-1', null, '移动待办 APP', '移动端待办应用整体需求包。', 'DESIGN'),
      n('REQ-1-1', 'REQ-1', '底部导航', '底部 Tab 栏切换页面。', 'DESIGN'),
      n('REQ-1-1-1', 'REQ-1-1', '列表页 Tab', '首页展示任务列表。', 'IMPLEMENT'),
      n('REQ-1-1-2', 'REQ-1-1', '我的页 Tab', '个人中心入口。', 'IMPLEMENT'),
      n('REQ-1-2', 'REQ-1', '列表页', '任务卡片列表与滑动操作。', 'DESIGN'),
      n('REQ-1-2-1', 'REQ-1-2', '任务卡片', '单条任务卡片渲染。', 'IMPLEMENT'),
      n('REQ-1-2-2', 'REQ-1-2', '左滑删除', '滑动显示删除按钮。', 'IMPLEMENT'),
      n('REQ-1-3', 'REQ-1', '添加页', '底部弹出的添加表单。', 'DESIGN'),
      n('REQ-1-3-1', 'REQ-1-3', '表单输入', '标题与日期选择。', 'IMPLEMENT'),
      n('REQ-1-3-2', 'REQ-1-3', 'FAB 悬浮按钮', '右下角加号唤起添加页。', 'IMPLEMENT'),
    ],
  };
}

// ===== 历史记录 =====
export interface HistoryItem {
  taskId: string;
  title: string;
  appType: string;
  status: string;
  createdAt: string;
  totalNodes: number;
  passedNodes: number;
}

// ===== Mock 测试用例（待办清单）=====
export const MOCK_TESTS: TestCase[] = [
  { id: 'TC-001', name: '输入标题并添加任务成功', status: 'PASSED', relatedReq: 'REQ-1-1-1', duration: 1.8 },
  { id: 'TC-002', name: '空标题添加被拦截', status: 'PASSED', relatedReq: 'REQ-1-1-1', duration: 1.2 },
  { id: 'TC-003', name: '点击复选框完成任务', status: 'PASSED', relatedReq: 'REQ-1-1-2', duration: 1.5 },
  { id: 'TC-004', name: '已完成任务划线展示', status: 'PASSED', relatedReq: 'REQ-1-1-2', duration: 1.1 },
  { id: 'TC-005', name: '删除单条任务', status: 'PASSED', relatedReq: 'REQ-1-1-3', duration: 1.3 },
  { id: 'TC-006', name: '为任务设置截止日期', status: 'PASSED', relatedReq: 'REQ-1-2-1', duration: 2.0 },
  { id: 'TC-007', name: '按"今天"筛选任务', status: 'PASSED', relatedReq: 'REQ-1-2-2', duration: 2.2 },
  { id: 'TC-008', name: '刷新后任务不丢失', status: 'PASSED', relatedReq: 'REQ-1-3-1', duration: 2.6 },
  { id: 'TC-009', name: '无任务时空状态展示', status: 'PASSED', relatedReq: 'REQ-1-4-1', duration: 1.0 },
  { id: 'TC-010', name: '按"已过期"筛选遗漏今日任务', status: 'FAILED', relatedReq: 'REQ-1-2-2', duration: 3.1, failReason: '截止日期为今天 23:59 的任务被误判为已过期。' },
  { id: 'TC-011', name: '快速连续添加任务渲染错乱', status: 'FAILED', relatedReq: 'REQ-1-1-1', duration: 2.8, failReason: '100ms 内连续添加时列表索引 Key 冲突。' },
];

// ===== 编译日志模板 =====
export interface LogTemplate {
  level: 'info' | 'success' | 'warn' | 'error' | 'system';
  message: string;
}

export function buildCompileLogs(): LogTemplate[] {
  return [
    { level: 'system', message: 'ARC Studio 编译会话已启动' },
    { level: 'info', message: '加载需求框架：待办清单应用（12 个节点）' },
    { level: 'info', message: '选择接口配置：API Base = https://api.deepseek.com/v1' },
    { level: 'info', message: '进入【需求设计】阶段，模型 deepseek-v4-pro' },
    { level: 'info', message: '解析自然语言需求，拆解一级模块...' },
    { level: 'success', message: 'REQ-1 需求包拆解完成' },
    { level: 'info', message: 'REQ-1-1 任务核心管理 · 开始设计' },
    { level: 'success', message: 'REQ-1-1 任务核心管理 · 设计通过' },
    { level: 'info', message: 'REQ-1-2 日期与筛选 · 开始设计' },
    { level: 'success', message: 'REQ-1-2 日期与筛选 · 设计通过' },
    { level: 'info', message: 'REQ-1-3 数据持久化 · 开始设计' },
    { level: 'success', message: 'REQ-1-3 数据持久化 · 设计通过' },
    { level: 'info', message: '进入【测试生成】阶段，模型 qwen3.7-plus' },
    { level: 'info', message: '根据设计生成测试用例（11 条）...' },
    { level: 'success', message: 'REQ-1-4 界面与交互 · 测试方案就绪' },
    { level: 'info', message: '进入【开发实现】阶段，模型 deepseek-v4-flash' },
    { level: 'info', message: 'REQ-1-1-1 添加任务 · 生成组件代码' },
    { level: 'success', message: 'REQ-1-1-1 添加任务 · 实现通过' },
    { level: 'info', message: 'REQ-1-1-2 打勾完成任务 · 生成组件代码' },
    { level: 'success', message: 'REQ-1-1-2 打勾完成任务 · 实现通过' },
    { level: 'info', message: 'REQ-1-1-3 删除任务 · 生成组件代码' },
    { level: 'success', message: 'REQ-1-1-3 删除任务 · 实现通过' },
    { level: 'info', message: 'REQ-1-2-1 设置截止日期 · 生成组件代码' },
    { level: 'success', message: 'REQ-1-2-1 设置截止日期 · 实现通过' },
    { level: 'warn', message: 'REQ-1-2-2 按日期筛选 · 边界日期判断需修正' },
    { level: 'error', message: 'REQ-1-2-2 按日期筛选 · 今日任务被误判为已过期' },
    { level: 'info', message: 'REQ-1-3-1 本地存储读写 · 生成组件代码' },
    { level: 'success', message: 'REQ-1-3-1 本地存储读写 · 实现通过' },
    { level: 'info', message: 'REQ-1-4-1 空状态引导 · 生成组件代码' },
    { level: 'success', message: 'REQ-1-4-1 空状态引导 · 实现通过' },
    { level: 'system', message: '编译完成，产出可运行应用预览' },
  ];
}

// ===== 演示模式：语音日历测试结果（15 条，12 通过 / 3 失败）=====
export const VOICE_CALENDAR_TESTS: TestCase[] = [
  { id: 'VC-001', name: '手机号注册并发送验证码', status: 'PASSED', relatedReq: 'REQ-1-1', duration: 2.1 },
  { id: 'VC-002', name: '密码加密存储（BCrypt）', status: 'PASSED', relatedReq: 'REQ-1-1', duration: 1.6 },
  { id: 'VC-003', name: '账号密码登录签发 Token', status: 'PASSED', relatedReq: 'REQ-1-2', duration: 1.8 },
  { id: 'VC-004', name: '未登录访问被守卫拦截跳转登录', status: 'PASSED', relatedReq: 'REQ-1-3', duration: 1.2 },
  { id: 'VC-005', name: '月视图正确渲染 6x7 日期网格', status: 'PASSED', relatedReq: 'REQ-2-1', duration: 2.4 },
  { id: 'VC-006', name: '新建并保存日程', status: 'PASSED', relatedReq: 'REQ-2-2', duration: 1.9 },
  { id: 'VC-007', name: '编辑与删除日程', status: 'PASSED', relatedReq: 'REQ-2-2', duration: 2.0 },
  { id: 'VC-008', name: '百度ASR语音转文字准确率', status: 'PASSED', relatedReq: 'REQ-3-1', duration: 3.5 },
  { id: 'VC-009', name: '自然语言解析"明天下午三点"', status: 'PASSED', relatedReq: 'REQ-3-2', duration: 2.8 },
  { id: 'VC-010', name: '语音指令自动创建日程', status: 'PASSED', relatedReq: 'REQ-3-3', duration: 3.0 },
  { id: 'VC-011', name: '日程到期推送系统通知', status: 'PASSED', relatedReq: 'REQ-4-1', duration: 2.2 },
  { id: 'VC-012', name: '前后端 /api 联调端口 8888', status: 'PASSED', relatedReq: 'REQ-5-1', duration: 2.6 },
  { id: 'VC-013', name: '日程分类标签渲染', status: 'FAILED', relatedReq: 'REQ-2-3', duration: 2.3, failReason: '分类颜色配置缺失，UI 渲染异常。' },
  { id: 'VC-014', name: '短信通道发送提醒', status: 'FAILED', relatedReq: 'REQ-4-2', duration: 3.1, failReason: 'SMS 服务未配置，发送失败。' },
  { id: 'VC-015', name: 'Schedule 表外键创建', status: 'FAILED', relatedReq: 'REQ-5-2', duration: 2.9, failReason: '外键约束冲突，Schedule 表创建失败。' },
];
