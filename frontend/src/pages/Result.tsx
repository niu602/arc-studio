import { useEffect, useState } from 'react';
import { Button, Card, List, Tag, Result as AntResult, Statistic, Tabs } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { MOCK_TESTS, VOICE_CALENDAR_TESTS } from '../mock/data';
import { getResult, mapTests, type ResultResponse } from '../services/api';
import type { TestCase } from '../types';

const statusTag: Record<string, { color: 'success' | 'error' | 'default'; text: string }> = {
  PASSED: { color: 'success', text: '通过' },
  FAILED: { color: 'error', text: '失败' },
  SKIPPED: { color: 'default', text: '跳过' },
};

export default function Result() {
  const navigate = useNavigate();
  const { taskId, appType, demoMode } = useApp();

  const [result, setResult] = useState<ResultResponse | null>(null);
  const [tests, setTests] = useState<TestCase[]>(demoMode ? VOICE_CALENDAR_TESTS : MOCK_TESTS);
  const [failed, setFailed] = useState(false);
  const [iframeError, setIframeError] = useState(false);

  useEffect(() => {
    if (demoMode) {
      setTests(VOICE_CALENDAR_TESTS);
      setFailed(false);
      return;
    }
    let cancelled = false;
    async function load() {
      if (!taskId) {
        setTests(MOCK_TESTS);
        return;
      }
      try {
        const r = await getResult(taskId);
        if (cancelled) return;
        setResult(r);
        setFailed((r.status || '').toUpperCase() === 'FAILED');
        if (r.test_results && r.test_results.length) {
          setTests(mapTests(r.test_results));
        }
      } catch (e) {
        console.warn('[ARC] 获取结果失败，使用本地演示数据', e);
        if (!cancelled) setTests(MOCK_TESTS);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  const previewUrl = result?.preview_url || '';
  const downloadUrl = result?.download_url || '';

  const handleDownload = () => {
    if (demoMode) {
      // 演示模式：优先请求后端 demo-download，失败则降级文本占位
      const a = document.createElement('a');
      a.href = '/api/demo-download';
      a.download = 'voice-calendar.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      return;
    }
    if (downloadUrl) {
      window.open(downloadUrl, '_blank');
      return;
    }
    // mock 下载
    const blob = new Blob(['ARC Studio mock output\n'], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'arc-app-output.zip';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <AntResult
        status={failed ? 'error' : 'success'}
        title={failed ? '编译完成，但有失败项' : '编译完成！'}
        subTitle={failed ? '部分节点未通过，请查看下方测试结果' : '你的应用已经生成，可以在下方预览'}
      />

      {/* 应用预览 */}
      <Card title="应用预览" style={{ borderRadius: 12, marginBottom: 16 }}>
        {demoMode ? (
          <VoiceCalendarPreview />
        ) : previewUrl && !iframeError ? (
          <iframe
            src={previewUrl}
            title="应用预览"
            onError={() => setIframeError(true)}
            style={{ width: '100%', height: 480, border: '1px solid #e0e0e0', borderRadius: 8 }}
          />
        ) : appType === 'mobile' ? (
          <MobilePreviewMock />
        ) : (
          <TodoPreviewMock />
        )}
      </Card>

      {/* 概要统计 */}
      {result?.summary && (
        <Card style={{ borderRadius: 12, marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
            <Statistic title="总节点" value={result.summary.total_nodes} />
            <Statistic title="通过" value={result.summary.passed_nodes} valueStyle={{ color: '#2ecc71' }} />
            <Statistic title="失败" value={result.summary.failed_nodes} valueStyle={{ color: '#e74c3c' }} />
            <Statistic title="总耗时" value={`${Math.round(result.summary.total_time_seconds / 60)}m`} />
            <Statistic title="总成本" value={result.summary.total_cost} precision={2} prefix="¥" />
          </div>
        </Card>
      )}

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        <Card title={`测试结果（${tests.length} 条）`} style={{ flex: 1, minWidth: 0, borderRadius: 12 }}>
          <List
            size="small"
            dataSource={tests}
            renderItem={(t) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <span>
                      <span style={{ color: '#8494a7', marginRight: 8, fontSize: 12 }}>{t.id}</span>
                      {t.name}
                    </span>
                  }
                  description={t.failReason}
                />
                <Tag color={statusTag[t.status].color}>{statusTag[t.status].text}</Tag>
              </List.Item>
            )}
          />
        </Card>

        <Card style={{ width: 300, flexShrink: 0, borderRadius: 12 }}>
          <Button type="primary" size="large" block icon={<DownloadOutlined />} onClick={handleDownload} style={{ marginBottom: 12 }}>
            下载代码包
          </Button>
          <Button block onClick={() => navigate('/compile')} style={{ marginBottom: 12 }}>
            重新编译
          </Button>
          <Button block onClick={() => navigate('/')}>
            返回首页
          </Button>
        </Card>
      </div>
    </div>
  );
}

// 模拟一个待办清单 UI
function TodoPreviewMock() {
  const items = [
    { text: '学习 React', done: true },
    { text: '买菜', done: false },
    { text: '完成 ARC Studio 前端', done: false },
  ];
  return (
    <div style={{ background: '#f0f5ff', borderRadius: 12, padding: 20, height: 400, overflow: 'auto' }}>
      <div
        style={{
          maxWidth: 360,
          margin: '0 auto',
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 4px 16px rgba(0,0,0,.08)',
          padding: 20,
        }}
      >
        <h3 style={{ marginTop: 0 }}>我的待办</h3>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            placeholder="添加任务..."
            style={{ flex: 1, height: 32, padding: '0 10px', borderRadius: 6, border: '1px solid #d9d9d9' }}
          />
          <Button type="primary">添加</Button>
        </div>
        {items.map((it, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
            <input type="checkbox" defaultChecked={it.done} readOnly />
            <span style={{ textDecoration: it.done ? 'line-through' : 'none', color: it.done ? '#aaa' : '#333' }}>
              {it.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// 移动端 mock 预览：手机外框
function MobilePreviewMock() {
  const items = [
    { text: '学习 React', done: true },
    { text: '买菜', done: false },
    { text: '完成 ARC Studio', done: false },
  ];
  return (
    <div style={{ background: '#eef2f7', borderRadius: 12, padding: 20, height: 480, overflow: 'auto' }}>
      <div
        style={{
          width: 375,
          margin: '0 auto',
          background: '#111',
          borderRadius: 36,
          padding: 12,
          boxShadow: '0 8px 30px rgba(0,0,0,.25)',
        }}
      >
        <div style={{ background: '#fff', borderRadius: 26, height: 420, overflow: 'auto', padding: 16 }}>
          <div style={{ textAlign: 'center', fontWeight: 700, marginBottom: 12 }}>我的待办</div>
          {items.map((it, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid #f0f0f0' }}>
              <input type="checkbox" defaultChecked={it.done} readOnly />
              <span style={{ textDecoration: it.done ? 'line-through' : 'none', color: it.done ? '#aaa' : '#333' }}>
                {it.text}
              </span>
            </div>
          ))}
          <div style={{ marginTop: 24, background: '#f7f7f7', borderRadius: 12, padding: 12, textAlign: 'center', color: '#1677ff' }}>
            ＋ 新建任务
          </div>
        </div>
      </div>
    </div>
  );
}

// 演示模式：语音日历双 Tab 预览（登录页 + 月视图日历）
function VoiceCalendarPreview() {
  const week = ['日', '一', '二', '三', '四', '五', '六'];
  // 9月1日为周二（2026-09-01 实际为周二），构造日期网格
  const leading = 2; // 1号前面占2格（日、一）
  const days = Array.from({ length: 30 }, (_, i) => i + 1);
  const events: Record<number, { label: string; color: string }> = {
    15: { label: '团队会议', color: '#1677ff' },
    20: { label: '项目截止', color: '#e74c3c' },
    25: { label: '语音录入测试', color: '#2ecc71' },
  };
  const today = 30;

  const cells: (number | null)[] = [
    ...Array.from({ length: leading }, () => null),
    ...days,
  ];

  return (
    <div style={{ height: 480, overflow: 'hidden', borderRadius: 8 }}>
      <Tabs
        defaultActiveKey="calendar"
        items={[
          {
            key: 'login',
            label: '登录页',
            children: (
              <div
                style={{
                  height: 420,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'linear-gradient(135deg,#e8f1ff 0%,#f6f9ff 100%)',
                }}
              >
                <div
                  style={{
                    width: 340,
                    background: '#fff',
                    borderRadius: 12,
                    boxShadow: '0 8px 30px rgba(22,119,255,.12)',
                    padding: '32px 28px',
                  }}
                >
                  <h2 style={{ textAlign: 'center', marginTop: 0, color: '#1677ff' }}>语音日历</h2>
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 13, color: '#8494a7', marginBottom: 6 }}>手机号</div>
                    <div style={{ height: 38, border: '1px solid #d9d9d9', borderRadius: 6, padding: '0 12px', lineHeight: '36px', color: '#bbb' }}>
                      请输入手机号
                    </div>
                  </div>
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 13, color: '#8494a7', marginBottom: 6 }}>密码</div>
                    <div style={{ height: 38, border: '1px solid #d9d9d9', borderRadius: 6, padding: '0 12px', lineHeight: '36px', color: '#bbb' }}>
                      请输入密码
                    </div>
                  </div>
                  <div style={{ height: 40, background: '#1677ff', color: '#fff', borderRadius: 6, textAlign: 'center', lineHeight: '40px', fontWeight: 600 }}>
                    登录
                  </div>
                  <div style={{ textAlign: 'center', marginTop: 14, color: '#1677ff', fontSize: 13 }}>
                    没有账号？立即注册
                  </div>
                </div>
              </div>
            ),
          },
          {
            key: 'calendar',
            label: '日历主页',
            children: (
              <div style={{ height: 420, padding: '16px 24px', background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <span style={{ fontSize: 18, fontWeight: 700 }}>‹ 2026年9月 ›</span>
                  <span style={{ color: '#8494a7', fontSize: 13 }}>今日日程</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 4 }}>
                  {week.map((w) => (
                    <div key={w} style={{ textAlign: 'center', color: '#8494a7', fontSize: 13, padding: '6px 0' }}>
                      {w}
                    </div>
                  ))}
                  {cells.map((d, i) => (
                    <div
                      key={i}
                      style={{
                        minHeight: 44,
                        background: d === today ? '#1677ff' : '#f7f9fc',
                        color: d === today ? '#fff' : '#333',
                        borderRadius: 6,
                        padding: 4,
                        fontSize: 12,
                      }}
                    >
                      {d ?? ''}
                      {d != null && events[d] && (
                        <div
                          style={{
                            marginTop: 2,
                            background: events[d].color,
                            color: '#fff',
                            borderRadius: 3,
                            fontSize: 10,
                            textAlign: 'center',
                            padding: '1px 0',
                          }}
                        >
                          {events[d].label}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 14, background: '#f0f5ff', borderRadius: 8, padding: '10px 14px' }}>
                  <div style={{ fontSize: 13, color: '#1677ff', fontWeight: 600 }}>今日 · 9月30日</div>
                  <div style={{ fontSize: 13, color: '#5a6b7b', marginTop: 4 }}>· 15:00 语音录入产品评审会</div>
                  <div style={{ fontSize: 13, color: '#5a6b7b', marginTop: 2 }}>· 18:30 健身计划提醒</div>
                </div>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
