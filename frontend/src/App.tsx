import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import AppLayout from './components/Layout/AppLayout';
import Home from './pages/Home';
import CreateProject from './pages/CreateProject';
import ModelConfig from './pages/ModelConfig';
import Compile from './pages/Compile';
import Result from './pages/Result';
import History from './pages/History';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/create" element={<CreateProject />} />
            <Route path="/models" element={<ModelConfig />} />
            <Route path="/result" element={<Result />} />
            <Route path="/history" element={<History />} />
          </Route>
          {/* 编译页不套布局（顶栏隐藏） */}
          <Route path="/compile" element={<Compile />} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
