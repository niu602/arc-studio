import { Button, Card, Col, Row, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { CodeOutlined, RocketOutlined, KeyOutlined } from '@ant-design/icons';

const MODELS = ['deepseek-v4-pro', 'deepseek-v4-flash', 'qwen3.7-plus', 'glm-5.3-flash'];
const STACK = ['React', 'FastAPI', 'LangGraph'];

const FEATURES = [
  {
    icon: <CodeOutlined style={{ fontSize: 32, color: '#1677ff' }} />,
    title: '不用写代码',
    desc: '用自然语言描述需求，AI 自动拆解并实现。',
  },
  {
    icon: <RocketOutlined style={{ fontSize: 32, color: '#1677ff' }} />,
    title: '多模型可选',
    desc: '设计、测试、开发三个阶段自由搭配不同 AI 模型。',
  },
  {
    icon: <KeyOutlined style={{ fontSize: 32, color: '#1677ff' }} />,
    title: '自己的 Key 自己的额度',
    desc: '填入你自己的 API Key，平台不收费，花多少你说了算。',
  },
];

export default function Home() {
  const navigate = useNavigate();
  return (
    <div>
      {/* Hero */}
      <div
        style={{
          background:
            'linear-gradient(135deg,#0a1628 0%,#0d2847 40%,#0b3d6e 70%,#1677ff 100%)',
          borderRadius: 16,
          padding: '64px 48px',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <h1 style={{ color: '#fff', fontSize: 40, marginBottom: 16 }}>用大白话，做出你的应用</h1>
        <p style={{ color: '#a8d4ff', fontSize: 18 }}>
          不会写代码？告诉 AI 你想要什么，它帮你做出来
        </p>
        <Button
          type="primary"
          size="large"
          style={{ marginTop: 28, height: 48, padding: '0 36px', fontSize: 16 }}
          onClick={() => navigate('/create')}
        >
          开始创建
        </Button>
      </div>

      {/* 卖点卡片 */}
      <Row gutter={[24, 24]} style={{ marginTop: 32 }}>
        {FEATURES.map((f) => (
          <Col xs={24} md={8} key={f.title}>
            <Card hoverable style={{ height: '100%', textAlign: 'center', borderRadius: 12 }}>
              <div style={{ marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{ marginBottom: 8 }}>{f.title}</h3>
              <p style={{ color: '#8494a7', marginBottom: 0 }}>{f.desc}</p>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 底部模型与技术栈 */}
      <Card style={{ marginTop: 32, borderRadius: 12, textAlign: 'center' }}>
        <div style={{ color: '#8494a7', marginBottom: 12 }}>支持的模型</div>
        <div style={{ marginBottom: 20 }}>
          {MODELS.map((m) => (
            <Tag key={m} color="blue" style={{ marginBottom: 6 }}>
              {m}
            </Tag>
          ))}
        </div>
        <div style={{ color: '#8494a7', marginBottom: 8 }}>技术栈</div>
        <div>
          {STACK.map((s) => (
            <Tag key={s} style={{ marginBottom: 6 }}>
              {s}
            </Tag>
          ))}
        </div>
      </Card>
    </div>
  );
}
