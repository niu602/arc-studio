import { useMemo, useState } from 'react';
import { Button, Card, Col, Form, Input, Row, Select, Progress, Alert, App, Switch } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import {
  MODEL_OPTIONS,
  MODEL_PRICES,
  PHASE_LABELS,
  allProCost,
  totalCost,
  phaseCost,
} from '../mock/data';
import type { ModelSelection, PhaseKey } from '../types';

const PHASES: PhaseKey[] = ['interface', 'testgen', 'tdd'];

export default function ModelConfig() {
  const navigate = useNavigate();
  const { models, saveApiConfig, apiConfigured, refreshApiStatus, demoMode, setDemoMode } = useApp();
  const { message } = App.useApp();

  const [sel, setSel] = useState<ModelSelection>(models);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('arc_api_key') ?? '');
  const [baseUrl, setBaseUrl] = useState(() => localStorage.getItem('arc_base_url') ?? 'https://api.deepseek.com/v1');

  const currentCost = useMemo(() => totalCost(sel), [sel]);
  const proCost = useMemo(() => allProCost(), []);
  const savePct = proCost > 0 ? Math.max(0, Math.round(((proCost - currentCost) / proCost) * 100)) : 0;

  const handleSave = () => {
    if (!apiKey.trim()) {
      message.warning('请填写 API Key');
      return;
    }
    saveApiConfig(apiKey.trim(), baseUrl.trim() || 'https://api.deepseek.com/v1', sel);
    message.success('配置已保存到本地');
    refreshApiStatus();
  };

  const handleStartCompile = () => {
    if (demoMode) {
      message.success('演示模式：即将使用内置模拟数据编译');
      navigate('/compile');
      return;
    }
    if (!apiConfigured && !apiKey.trim()) {
      message.warning('请先填写并保存 API Key，再开始编译');
      return;
    }
    // 即使未保存也先保存一次
    saveApiConfig(apiKey.trim(), baseUrl.trim() || 'https://api.deepseek.com/v1', sel);
    navigate('/compile');
  };

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>模型配置</h2>

      {/* 三阶段模型选择 */}
      <Row gutter={[16, 16]}>
        {PHASES.map((phase) => {
          const label = PHASE_LABELS[phase];
          const modelKey = sel[phase];
          const price = MODEL_PRICES[modelKey];
          const cost = phaseCost(modelKey, phase);
          return (
            <Col xs={24} md={8} key={phase}>
              <Card title={label.title} style={{ borderRadius: 12 }}>
                <div style={{ color: '#8494a7', marginBottom: 12, fontSize: 13 }}>{label.sub}</div>
                <div style={{ marginBottom: 8, color: '#5a6b7b' }}>模型</div>
                <Select
                  value={modelKey}
                  style={{ width: '100%', marginBottom: 12 }}
                  onChange={(v: string) => setSel((s) => ({ ...s, [phase]: v }))}
                  options={MODEL_OPTIONS.map((m) => ({ value: m, label: m }))}
                />
                <div style={{ fontSize: 13, color: '#5a6b7b' }}>
                  价格：输入 ¥{price?.in} / 百万 token · 输出 ¥{price?.out} / 百万 token
                </div>
                <div style={{ fontSize: 13, color: '#1677ff', marginTop: 8 }}>
                  本阶段预估：¥{cost.toFixed(2)}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* 成本预估 */}
      <Card title="成本预估" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={16}>
          <Col xs={24} md={8}>
            <div style={{ color: '#8494a7' }}>全用顶级模型</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>¥{proCost.toFixed(2)}</div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ color: '#8494a7' }}>当前配置</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1677ff' }}>¥{currentCost.toFixed(2)}</div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ color: '#8494a7', marginBottom: 6 }}>预计节省 {savePct}%</div>
            <Progress percent={savePct} strokeColor="#2ecc71" />
          </Col>
        </Row>
      </Card>

      {/* 演示模式开关 */}
      <Card
        style={{
          marginTop: 16,
          borderRadius: 12,
          borderColor: demoMode ? '#faad14' : undefined,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Switch checked={demoMode} onChange={(v) => setDemoMode(v)} />
          <div>
            <div style={{ fontWeight: 600 }}>
              使用演示模式（无需 API Key）
              {demoMode && <span style={{ marginLeft: 8, color: '#fa8c16' }}>● 已开启</span>}
            </div>
            <div style={{ color: '#8494a7', fontSize: 13 }}>
              开启后使用内置"语音日历"模拟数据跑通全流程，不消耗真实额度
            </div>
          </div>
        </div>
        {demoMode && (
          <Alert
            type="info"
            showIcon
            style={{ marginTop: 12 }}
            message="演示模式使用内置模拟数据，不消耗真实额度"
          />
        )}
      </Card>

      {/* API Key 配置 */}
      <Card title="API Key 配置" style={{ marginTop: 16, borderRadius: 12 }}>
        {!apiConfigured && !demoMode && (
          <Alert
            type="warning"
            showIcon
            message="尚未配置 API Key，保存后即可开始编译"
            style={{ marginBottom: 16 }}
          />
        )}
        <Form layout="vertical">
          <Form.Item label="API Key">
            <Input.Password
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              autoComplete="off"
              disabled={demoMode}
            />
          </Form.Item>
          <Form.Item label="Base URL">
            <Input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.deepseek.com/v1"
              disabled={demoMode}
            />
          </Form.Item>
          {!demoMode && <Button onClick={handleSave}>保存配置</Button>}
        </Form>
      </Card>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Button type="primary" size="large" onClick={handleStartCompile}>
          开始编译
        </Button>
      </div>
    </div>
  );
}
