import { Layout, Menu, Tag } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';

const { Header } = Layout;

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { apiConfigured, refreshApiStatus, demoMode } = useApp();

  // 编译进行中隐藏顶栏
  if (location.pathname === '/compile') return null;

  const selectedKey =
    location.pathname === '/'
      ? '/'
      : location.pathname === '/create'
        ? '/create'
        : location.pathname === '/models'
          ? '/models'
          : location.pathname;

  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        background: '#0d1b2a',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <div
        style={{
          color: '#fff',
          fontWeight: 700,
          fontSize: 18,
          marginRight: 32,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
        onClick={() => navigate('/')}
      >
        <span
          style={{
            width: 26,
            height: 26,
            borderRadius: 6,
            background: 'linear-gradient(135deg,#1677ff,#4ea1ff)',
            display: 'inline-block',
          }}
        />
        ARC Studio
      </div>
      <Menu
        theme="dark"
        mode="horizontal"
        selectedKeys={[selectedKey]}
        style={{ flex: 1, background: 'transparent', minWidth: 0 }}
        items={[
          { key: '/', label: '首页' },
          { key: '/create', label: '创建项目' },
          { key: '/models', label: '模型配置' },
          { key: '/history', label: '历史记录' },
        ]}
        onClick={({ key }) => {
          refreshApiStatus();
          navigate(key);
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {demoMode ? (
          <Tag color="warning" style={{ marginInlineEnd: 0 }}>
            演示模式
          </Tag>
        ) : (
          <Tag color={apiConfigured ? 'success' : 'warning'} style={{ marginInlineEnd: 0 }}>
            {apiConfigured ? 'API Key 已配置' : 'API Key 未配置'}
          </Tag>
        )}
      </div>
    </Header>
  );
}
