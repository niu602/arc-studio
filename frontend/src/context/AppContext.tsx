import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { ModelSelection, RequirementTree } from '../types';
import { DEFAULT_MODELS, buildTodoTree } from '../mock/data';
import { getApiKey, getBaseUrl, getModels, setApiKey, setBaseUrl, setModels, getDemoMode, setDemoMode as persistDemoMode } from '../utils/storage';

interface AppContextValue {
  tree: RequirementTree | null;
  setTree: (t: RequirementTree | null) => void;

  models: ModelSelection;
  setModelsConfig: (m: ModelSelection) => void;

  apiKey: string;
  baseUrl: string;
  apiConfigured: boolean;
  saveApiConfig: (key: string, base: string, models: ModelSelection) => void;
  refreshApiStatus: () => void;

  // 编译任务相关（页面间传递）
  taskId: string | null;
  setTaskId: (id: string | null) => void;
  requirementText: string;
  setRequirementText: (s: string) => void;
  requirementYaml: string;
  setRequirementYaml: (s: string) => void;
  appType: 'web' | 'mobile';
  setAppType: (t: 'web' | 'mobile') => void;

  demoMode: boolean;
  setDemoMode: (v: boolean) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [tree, setTree] = useState<RequirementTree | null>(null);
  const [models, setModelsState] = useState<ModelSelection>(() => getModels() ?? DEFAULT_MODELS);
  const [apiKey, setApiKeyState] = useState<string>(() => getApiKey());
  const [baseUrl, setBaseUrlState] = useState<string>(() => getBaseUrl());

  const [taskId, setTaskId] = useState<string | null>(null);
  const [requirementText, setRequirementText] = useState('');
  const [requirementYaml, setRequirementYaml] = useState('');
  const [appType, setAppType] = useState<'web' | 'mobile'>('web');
  const [demoMode, setDemoModeState] = useState<boolean>(() => getDemoMode());

  const setDemoMode = useCallback((v: boolean) => {
    persistDemoMode(v);
    setDemoModeState(v);
  }, []);

  const refreshApiStatus = useCallback(() => {
    setApiKeyState(getApiKey());
    setBaseUrlState(getBaseUrl());
  }, []);

  const saveApiConfig = useCallback((key: string, base: string, m: ModelSelection) => {
    setApiKey(key);
    setBaseUrl(base);
    setModels(m);
    setApiKeyState(key);
    setBaseUrlState(base);
    setModelsState(m);
  }, []);

  const setModelsConfig = useCallback((m: ModelSelection) => {
    setModels(m);
    setModelsState(m);
  }, []);

  const value = useMemo<AppContextValue>(
    () => ({
      tree,
      setTree,
      models,
      setModelsConfig,
      apiKey,
      baseUrl,
      apiConfigured: apiKey.trim().length > 0,
      saveApiConfig,
      refreshApiStatus,
      taskId,
      setTaskId,
      requirementText,
      setRequirementText,
      requirementYaml,
      setRequirementYaml,
      appType,
      setAppType,
      demoMode,
      setDemoMode,
    }),
    [tree, models, apiKey, baseUrl, saveApiConfig, setModelsConfig, refreshApiStatus, taskId, requirementText, requirementYaml, appType, demoMode, setDemoMode],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

// 供 Compile 页复用的默认树（若用户未先生成）
export { buildTodoTree };
