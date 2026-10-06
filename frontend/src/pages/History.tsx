import { useEffect, useState } from 'react';
import { Card, List, Tag, Progress, Empty, Button, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { getHistory } from '../utils/storage';
import { getServerHistory, type ServerHistoryItem } from '../services/api';
import type { HistoryItem } from '../mock/data';

const statusTag: Record<string, { color: 'success' | 'error' | 'warning' | 'default'; text: string }> = {
  COMPLETED: { color: 'success', text: '已完成' },
  FAILED: { color: 'error', text: '失败' },
  CANCELLED: { color: 'warning', text: '已取消' },
};

export default function History() {
  const navigate = useNavigate();
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    const local = getHistory();
    void getServerHistory().then((server) => {
      if (cancelled) return;
      if (!server.length) {
        setItems(local);
        return;
      }
      // 合并：服务器历史优先，补充本地
      const merged: HistoryItem[] = server.map((s: ServerHistoryItem) => ({
        taskId: s.task_id ?? `server_${Math.random()}`,
        title: s.title ?? '未命名项目',
        appType: s.app_type ?? 'web',
        status: s.status ?? 'COMPLETED',
        createdAt: s.created_at ?? new Date().toISOString(),
        totalNodes: s.total_nodes ?? 0,
        passedNodes: s.passed_nodes ?? 0,
      }));
      setItems([...merged, ...local]);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <Typography.Title level={3}>历史记录</Typography.Title>
      <Card style={{ borderRadius: 12 }}>
        {items.length === 0 ? (
          <Empty description="暂无编译记录" />
        ) : (
          <List
            dataSource={items}
            renderItem={(item) => {
              const passRate = item.totalNodes > 0 ? Math.round((item.passedNodes / item.totalNodes) * 100) : 0;
              const st = statusTag[item.status] ?? statusTag.COMPLETED;
              return (
                <List.Item
                  actions={[
                    <Button type="link" size="small" onClick={() => navigate(`/result?taskId=${item.taskId}`)}>
                      查看结果
                    </Button>,
                    <Button type="link" size="small" onClick={() => navigate('/create')}>
                      重新编译
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <span>
                        {item.title}
                        <Tag color={item.appType === 'mobile' ? 'purple' : 'blue'} style={{ marginLeft: 8 }}>
                          {item.appType === 'mobile' ? '移动' : 'Web'}
                        </Tag>
                        <Tag color={st.color} style={{ marginLeft: 4 }}>
                          {st.text}
                        </Tag>
                      </span>
                    }
                    description={
                      <div style={{ width: 280 }}>
                        <div style={{ color: '#8494a7', fontSize: 12, marginBottom: 4 }}>
                          {new Date(item.createdAt).toLocaleString()} · 通过 {item.passedNodes}/{item.totalNodes}
                        </div>
                        <Progress percent={passRate} size="small" strokeColor={item.status === 'FAILED' ? '#e74c3c' : '#2ecc71'} />
                      </div>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Card>
    </div>
  );
}
