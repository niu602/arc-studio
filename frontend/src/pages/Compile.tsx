import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, Progress, Statistic, App } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import RequirementTree from '../components/RequirementTree/RequirementTree';
import LogConsole from '../components/LogConsole/LogConsole';
import { buildCompileLogs, buildTodoTree, buildVoiceCalendarTree, DEMO_FAILED_NODES } from '../mock/data';
import {
  startCompile,
  getStatus,
  cancelCompile,
  mapNodes,
  mapLogLevel,
} from '../services/api';
import { addHistory } from '../utils/storage';
import type { LogLine, RequirementTree as RequirementTreeData } from '../types';

const FAILED_NODE = 'REQ-1-2-2';

function nowTime(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

export default function Compile() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const {
    tree,
    models,
    apiKey,
    baseUrl,
    requirementText,
    requirementYaml,
    taskId,
    setTaskId,
    appType,
    demoMode,
  } = useApp();

  const baseTree = useMemo(
    () => (demoMode ? buildVoiceCalendarTree() : tree ?? buildTodoTree()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tree, demoMode],
  );

  const [workTree, setWorkTree] = useState<RequirementTreeData>(() =>
    JSON.parse(JSON.stringify({ ...baseTree, nodes: baseTree.nodes.map((n) => ({ ...n, status: 'PENDING' })) })),
  );
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [progress, setProgress] = useState(0);
  const [phaseLabel, setPhaseLabel] = useState('正在编译...');
  const [elapsed, setElapsed] = useState(0);
  const [cost, setCost] = useState(0);
  const [done, setDone] = useState(false);

  const pollRef = useRef<number | null>(null);
  const elapsedTimer = useRef<number | null>(null);
  const timers = useRef<number[]>([]);
  const finishedRef = useRef(false);
  const startedRef = useRef(false);
  const logCountRef = useRef(0);

  const pushLog = (level: LogLine['level'], messageText: string) => {
    setLogs((prev) => [...prev, { time: nowTime(), level, message: messageText }]);
  };

  // 根据 current_node 生成"正在设计/开发：ID 名称"标签
  const labelForNode = (nodeId: string | undefined, stage: string): string => {
    if (!nodeId) return stage || '正在编译...';
    const node = workTree.nodes.find((n) => n.id === nodeId);
    const prefix = stage.includes('设计') ? '正在设计' : '正在开发';
    return node ? `${prefix}：${nodeId} ${node.name}` : `${prefix}：${nodeId}`;
  };

  const recordHistory = (status: string, tid: string, total: number, passed: number) => {
    addHistory({
      taskId: tid || `mock_${Date.now()}`,
      title: baseTree.title || requirementText,
      appType,
      status,
      createdAt: new Date().toISOString(),
      totalNodes: total,
      passedNodes: passed,
    });
  };

  // ===== Mock 动画（降级模式）=====
  const runMockAnimation = () => {
    pushLog('system', 'ARC Studio 编译会话已启动（本地演示）');
    pushLog('info', `加载需求框架：${baseTree.title}（${baseTree.nodes.length} 个节点）`);
    setPhaseLabel('正在编译...');

    const order = baseTree.nodes.map((n) => n.id);
    const logTemplates = buildCompileLogs();
    let logIdx = 0;
    const TICK = 1050;

    order.forEach((id, idx) => {
      const tStart = window.setTimeout(() => {
        if (finishedRef.current) return;
        setWorkTree((wt) => ({
          ...wt,
          nodes: wt.nodes.map((n) =>
            n.id === id ? { ...n, status: n.stage === 'DESIGN' ? 'DESIGNING' : 'IMPLEMENTING' } : n,
          ),
        }));
        setPhaseLabel(labelForNode(id, '开发阶段'));
        const lt = logTemplates[logIdx++];
        if (lt) pushLog(lt.level, lt.message);
      }, idx * TICK);

      const tEnd = window.setTimeout(() => {
        if (finishedRef.current) return;
        const failed = id === FAILED_NODE;
        setWorkTree((wt) => ({
          ...wt,
          nodes: wt.nodes.map((n) => (n.id === id ? { ...n, status: failed ? 'FAILED' : 'PASSED' } : n)),
        }));
        setCost((c) => c + (failed ? 0.02 : 0.01));
        setProgress(Math.round(((idx + 1) / order.length) * 100));
        const lt2 = logTemplates[logIdx++];
        if (lt2) pushLog(lt2.level, lt2.message);
      }, idx * TICK + TICK * 0.7);

      timers.current.push(tStart, tEnd);
    });

    const tFinish = window.setTimeout(() => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      setPhaseLabel('编译完成');
      setProgress(100);
      pushLog('success', '编译完成，已生成可运行应用');
      setDone(true);
      const passedCount = baseTree.nodes.length - 1;
      recordHistory('COMPLETED', `mock_${Date.now()}`, baseTree.nodes.length, passedCount);
      if (elapsedTimer.current) window.clearInterval(elapsedTimer.current);
      window.setTimeout(() => navigate('/result'), 1800);
    }, order.length * TICK + TICK * 1.2);
    timers.current.push(tFinish);
  };

  // ===== 演示模式：语音日历纯模拟编译 =====
  const runDemoAnimation = () => {
    pushLog('system', '【演示模式】编译会话已启动（不调用真实后端）');
    pushLog('info', `加载需求框架：${baseTree.title}（${baseTree.nodes.length} 个节点）`);
    pushLog('info', '阶段模型 → 设计:deepseek-v4-pro | 测试:qwen3.7-plus | 开发:deepseek-v4-flash');
    pushLog('info', '进入需求设计阶段，模型 deepseek-v4-pro');

    const order = baseTree.nodes.map((n) => n.id);
    const nodeMap = new Map(baseTree.nodes.map((n) => [n.id, n]));
    const TICK = 1000;
    const failReason: Record<string, string> = {
      'REQ-2-3': '分类颜色配置缺失，UI 渲染异常',
      'REQ-4-2': 'SMS 服务未配置，发送失败',
      'REQ-5-2': '外键约束冲突，Schedule 表创建失败',
    };

    // 阶段切换日志
    let lastStage = 'DESIGN';
    order.forEach((id, idx) => {
      const node = nodeMap.get(id)!;
      if (node.stage !== lastStage) {
        lastStage = node.stage;
        pushLog('info', node.stage === 'IMPLEMENT' ? '进入开发实现阶段，模型 deepseek-v4-flash' : '进入测试生成阶段，模型 qwen3.7-plus');
      }

      const tStart = window.setTimeout(() => {
        if (finishedRef.current) return;
        setWorkTree((wt) => ({
          ...wt,
          nodes: wt.nodes.map((n) =>
            n.id === id ? { ...n, status: n.stage === 'DESIGN' ? 'DESIGNING' : 'IMPLEMENTING' } : n,
          ),
        }));
        setPhaseLabel(labelForNode(id, node.stage === 'DESIGN' ? '需求设计阶段' : '开发实现阶段'));
        pushLog('info', `${id} ${node.name} · 开始处理`);
      }, idx * TICK);

      const tEnd = window.setTimeout(() => {
        if (finishedRef.current) return;
        const failed = DEMO_FAILED_NODES.includes(id);
        setWorkTree((wt) => ({
          ...wt,
          nodes: wt.nodes.map((n) => (n.id === id ? { ...n, status: failed ? 'FAILED' : 'PASSED' } : n)),
        }));
        setCost((c) => Math.round((c + (failed ? 0.02 : 0.021)) * 100) / 100);
        setProgress(Math.round(((idx + 1) / order.length) * 100));
        if (failed) {
          pushLog('error', `${id} ${node.name} · 实现失败：${failReason[id]}`);
        } else {
          pushLog('success', `${id} ${node.name} · 实现通过`);
        }
      }, idx * TICK + TICK * 0.7);

      timers.current.push(tStart, tEnd);
    });

    const tFinish = window.setTimeout(() => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      setPhaseLabel('编译完成');
      setProgress(100);
      setCost(0.35);
      pushLog('success', '编译完成（演示）：15 通过 / 3 失败，产出语音日历应用');
      setDone(true);
      const passed = baseTree.nodes.length - DEMO_FAILED_NODES.length;
      recordHistory('COMPLETED', `demo_${Date.now()}`, baseTree.nodes.length, passed);
      if (elapsedTimer.current) window.clearInterval(elapsedTimer.current);
      window.setTimeout(() => navigate('/result'), 1500);
    }, order.length * TICK + TICK * 1.2);
    timers.current.push(tFinish);
  };

  // ===== 真实编译模式 =====
  const runRealCompile = async () => {
    if (!apiKey.trim()) {
      message.warning('未配置 API Key，使用本地演示模式');
      runMockAnimation();
      return;
    }
    try {
      pushLog('info', `阶段模型 → 设计:${models.interface} | 测试:${models.testgen} | 开发:${models.tdd}`);
      const resp = await startCompile({
        requirement_text: requirementText,
        requirement_yaml: requirementYaml || undefined,
        app_type: appType,
        models: {
          design: models.interface,
          test: models.testgen,
          development: models.tdd,
        },
        api_key: apiKey,
        base_url: baseUrl,
      });
      const tid = resp.task_id;
      setTaskId(tid);
      pushLog('system', `编译任务已创建：${tid}`);
      pushLog('info', '等待后端执行...');

      pollRef.current = window.setInterval(async () => {
        if (finishedRef.current) return;
        try {
          const st = await getStatus(tid);
          // 更新节点
          const mappedNodes = mapNodes(st.nodes || []);
          if (mappedNodes.length) {
            setWorkTree((wt) => ({ ...wt, nodes: mappedNodes }));
          }
          // 追加新日志
          const backendLogs = st.logs || [];
          if (backendLogs.length > logCountRef.current) {
            const fresh = backendLogs.slice(logCountRef.current);
            logCountRef.current = backendLogs.length;
            setLogs((prev) => [
              ...prev,
              ...fresh.map((l) => ({
                time: l.timestamp ? l.timestamp.slice(11, 19) : nowTime(),
                level: mapLogLevel(l.level),
                message: l.message,
              })),
            ]);
          }
          // 统计
          if (typeof st.progress === 'number') setProgress(st.progress);
          if (st.current_node) {
            setPhaseLabel(labelForNode(st.current_node, st.current_stage || ''));
          } else if (st.current_stage) {
            setPhaseLabel(st.current_stage);
          }
          if (st.stats) {
            setElapsed(st.stats.elapsed_seconds ?? 0);
            setCost(st.stats.estimated_cost ?? 0);
          }

          const status = (st.status || '').toUpperCase();
          if (status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED') {
            finishedRef.current = true;
            if (pollRef.current) window.clearInterval(pollRef.current);
            if (elapsedTimer.current) window.clearInterval(elapsedTimer.current);
            setDone(true);
            setProgress(100);
            const passed = (st.nodes || []).filter((n) => (n.status || '').toUpperCase() === 'PASSED').length;
            recordHistory(status, tid, (st.nodes || []).length, passed);
            setPhaseLabel(status === 'COMPLETED' ? '编译完成' : status === 'FAILED' ? '编译失败' : '已取消');
            pushLog(status === 'COMPLETED' ? 'success' : 'error', `任务状态：${status}`);
            window.setTimeout(() => navigate('/result'), 1500);
          }
        } catch (pollErr) {
          console.warn('[ARC] 轮询状态失败', pollErr);
        }
      }, 2000);
    } catch (e) {
      console.warn('[ARC] 启动编译失败，降级为本地演示模式', e);
      pushLog('error', '启动编译失败，降级为本地演示');
      runMockAnimation();
    }
  };

  useEffect(() => {
    elapsedTimer.current = window.setInterval(() => setElapsed((e) => e + 1), 1000);

    // 防止 React StrictMode 开发环境下 effect 双调用导致重复创建编译任务
    if (startedRef.current) return;
    startedRef.current = true;

    if (demoMode) {
      runDemoAnimation();
    } else if (requirementText && !taskId) {
      void runRealCompile();
    } else {
      runMockAnimation();
    }

    return () => {
      timers.current.forEach((t) => window.clearTimeout(t));
      if (pollRef.current) window.clearInterval(pollRef.current);
      if (elapsedTimer.current) window.clearInterval(elapsedTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doneCount = workTree.nodes.filter((n) => n.status === 'PASSED' || n.status === 'FAILED').length;

  const handleCancel = async () => {
    finishedRef.current = true;
    timers.current.forEach((t) => window.clearTimeout(t));
    if (pollRef.current) window.clearInterval(pollRef.current);
    if (elapsedTimer.current) window.clearInterval(elapsedTimer.current);
    if (taskId) {
      try {
        await cancelCompile(taskId);
      } catch (e) {
        console.warn('[ARC] 取消编译请求失败', e);
      }
    }
    navigate('/');
  };

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const ss = String(Math.floor(elapsed % 60)).padStart(2, '0');

  return (
    <div>
      <Card style={{ borderRadius: 12, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ color: '#5a6b7b', fontWeight: 600 }}>{phaseLabel}</span>
          <span style={{ color: '#1677ff', fontWeight: 600 }}>{progress}%</span>
        </div>
        <Progress percent={progress} strokeColor={{ from: '#1677ff', to: '#4ea1ff' }} />
      </Card>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <RequirementTree tree={workTree} height={360} />
          <div style={{ marginTop: 16 }}>
            <LogConsole logs={logs} height={240} />
          </div>
        </div>

        <Card title="编译统计" style={{ width: 260, flexShrink: 0, borderRadius: 12 }}>
          <Statistic title="已完成节点" value={`${doneCount} / ${workTree.nodes.length}`} />
          <div style={{ height: 16 }} />
          <Statistic title="已耗时" value={`${mm}:${ss}`} />
          <div style={{ height: 16 }} />
          <Statistic title="已花费" value={cost} precision={2} prefix="¥" />
          <div style={{ height: 24 }} />
          <Button danger block disabled={done} onClick={handleCancel}>
            取消编译
          </Button>
        </Card>
      </div>
    </div>
  );
}
