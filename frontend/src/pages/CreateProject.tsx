import { useState } from 'react';
import { Button, Card, Drawer, Input, Radio, Spin, Tag, App } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import RequirementTree from '../components/RequirementTree/RequirementTree';
import { buildTodoTree, buildMobileTodoTree, buildVoiceCalendarTree } from '../mock/data';
import { generateTree, mapGenerateTree } from '../services/api';
import { getApiKey, getBaseUrl } from '../utils/storage';
import type { ReqNode } from '../types';

const { TextArea } = Input;

const stageLabel: Record<ReqNode['stage'], string> = {
  DESIGN: '需求设计',
  TEST: '测试生成',
  IMPLEMENT: '开发实现',
};

const statusLabel: Record<ReqNode['status'], { text: string; color: string }> = {
  PENDING: { text: '待处理', color: 'default' },
  DESIGNING: { text: '进行中', color: 'processing' },
  IMPLEMENTING: { text: '进行中', color: 'processing' },
  PASSED: { text: '成功', color: 'success' },
  FAILED: { text: '失败', color: 'error' },
};

export default function CreateProject() {
  const navigate = useNavigate();
  const { tree, setTree, setRequirementText, setRequirementYaml, appType, setAppType, demoMode } = useApp();
  const { message } = App.useApp();
  const [desc, setDesc] = useState('');
  const [generating, setGenerating] = useState(false);
  const [drawerNode, setDrawerNode] = useState<ReqNode | null>(null);

  // 演示模式：直接用内置语音日历树，模拟短暂加载
  const doGenerateDemo = (text: string) => {
    setGenerating(true);
    window.setTimeout(() => {
      setTree(buildVoiceCalendarTree());
      setRequirementText(text || '语音日历应用：用语音快速创建和管理日程');
      setRequirementYaml('');
      setGenerating(false);
      message.success('演示模式：已生成语音日历需求框架');
    }, 800);
  };

  // 调用后端生成需求树，失败降级为 mock
  const doGenerate = async (text: string, type: 'web' | 'mobile') => {
    if (demoMode) {
      doGenerateDemo(text);
      return;
    }
    setGenerating(true);
    try {
      const apiKey = getApiKey();
      const baseUrl = getBaseUrl();
      const resp = await generateTree(text, type, apiKey || undefined, baseUrl || undefined);
      const t = mapGenerateTree(resp);
      setTree(t);
      setRequirementText(text);
      setRequirementYaml(resp.requirement_yaml ?? '');
      message.success(resp.source === 'llm' ? '需求框架已由模型生成' : '需求框架已生成');
    } catch (e) {
      console.warn('[ARC] generate-tree 失败，降级为本地演示数据', e);
      setTree(type === 'mobile' ? buildMobileTodoTree() : buildTodoTree());
      setRequirementText(text);
      setRequirementYaml('');
      message.warning('后端不可用，使用本地演示数据');
    } finally {
      setGenerating(false);
    }
  };

  const handleUseTemplate = () => {
    const tpl = '做一个语音日历应用：用语音录入日程，能语音创建、管理日程，登录后按月历查看，到期提醒。';
    setDesc(tpl);
    doGenerateDemo(tpl);
  };

  const handleGenerate = () => {
    if (!desc.trim()) {
      message.warning('请先描述你想要的应用');
      return;
    }
    void doGenerate(desc.trim(), appType);
  };

  const handleRegenerate = () => {
    void doGenerate(desc.trim() || '待办清单应用', appType);
  };

  const nodeById = (id: string): ReqNode | undefined => tree?.nodes.find((n) => n.id === id);

  return (
    <div>
      <div style={{ display: 'flex', gap: 24 }}>
        {/* 左侧输入区 40% */}
        <div style={{ width: '40%', flexShrink: 0 }}>
          <Card title="描述你的应用" style={{ borderRadius: 12 }}>
            <TextArea
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              autoSize={{ minRows: 5, maxRows: 12 }}
              placeholder={
                demoMode
                  ? '演示模式：输入任意需求，将使用内置「语音日历」模板生成...\n\n例如：做一个能语音录入日程、按月历查看、到期提醒的语音日历应用。'
                  : '用大白话描述你想要的应用...\n\n例如：我要一个待办清单应用，能添加任务、打勾完成、删除任务，还能按日期筛选。'
              }
              style={{ marginBottom: 16 }}
            />
            {demoMode && (
              <Button type="dashed" block style={{ marginBottom: 16 }} onClick={handleUseTemplate} loading={generating}>
                使用语音日历模板
              </Button>
            )}
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, color: '#8494a7' }}>应用类型</div>
              <Radio.Group
                value={appType}
                onChange={(e) => setAppType(e.target.value)}
                options={[
                  { label: 'Web 应用', value: 'web' },
                  { label: '移动应用', value: 'mobile' },
                ]}
                optionType="button"
              />
            </div>
            <Button type="primary" size="large" block loading={generating} onClick={handleGenerate}>
              {generating ? '正在生成...' : '生成需求框架'}
            </Button>
          </Card>
        </div>

        {/* 右侧需求树 60% */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Card
            title="需求框架"
            style={{ borderRadius: 12 }}
            extra={
              tree ? (
                <Button onClick={handleRegenerate} loading={generating}>
                  重新生成
                </Button>
              ) : undefined
            }
          >
            {generating && !tree ? (
              <div style={{ height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Spin size="large" />
              </div>
            ) : tree ? (
              <>
                <RequirementTree tree={tree} height={420} onNodeClick={(id) => setDrawerNode(nodeById(id) ?? null)} />
                <div style={{ marginTop: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
                  <span style={{ color: '#8494a7' }}>这个框架对吗？</span>
                  <Button type="primary" onClick={() => navigate('/models')}>
                    确认，下一步
                  </Button>
                  <Button onClick={handleRegenerate}>重新生成</Button>
                </div>
              </>
            ) : (
              <div
                style={{
                  height: 420,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#8494a7',
                  background: '#0d1b2a',
                  borderRadius: 12,
                }}
              >
                在左侧输入需求，点击生成按钮
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* 节点详情 Drawer */}
      <Drawer
        open={!!drawerNode}
        title={drawerNode ? `${drawerNode.id} · ${drawerNode.name}` : ''}
        width={380}
        onClose={() => setDrawerNode(null)}
      >
        {drawerNode && (
          <div>
            <DetailRow k="描述" v={drawerNode.desc} />
            <DetailRow k="所属阶段" v={stageLabel[drawerNode.stage]} />
            <DetailRow k="使用模型" v={drawerNode.model} />
            <DetailRow k="预计耗时" v={drawerNode.duration ? `${drawerNode.duration}s` : '—'} />
            <DetailRow
              k="状态"
              v={<Tag color={statusLabel[drawerNode.status].color}>{statusLabel[drawerNode.status].text}</Tag>}
            />
          </div>
        )}
      </Drawer>
    </div>
  );
}

function DetailRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px dashed #f0f0f0' }}>
      <span style={{ color: '#8494a7' }}>{k}</span>
      <span style={{ textAlign: 'right', maxWidth: '62%' }}>{v}</span>
    </div>
  );
}
