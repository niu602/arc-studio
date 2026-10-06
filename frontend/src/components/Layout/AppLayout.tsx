import { Layout } from 'antd';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

const { Content, Footer } = Layout;

export default function AppLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Navbar />
      <Content style={{ background: '#f5f5f5' }}>
        <div
          style={{
            maxWidth: 1400,
            margin: '0 auto',
            padding: 24,
          }}
        >
          <Outlet />
        </div>
      </Content>
      <Footer style={{ textAlign: 'center', background: '#f5f5f5', color: '#8494a7' }}>
        ARC Studio ©2026 · 用大白话，做出你的应用
      </Footer>
    </Layout>
  );
}
