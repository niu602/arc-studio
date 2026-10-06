import { useEffect, useRef } from 'react';
import type { LogLine } from '../../types';

const levelColor: Record<LogLine['level'], string> = {
  info: '#7ea8d4',
  success: '#6ee7a8',
  warn: '#ffc857',
  error: '#ff8a80',
  system: '#b388ff',
};

interface Props {
  logs: LogLine[];
  height?: number;
}

export default function LogConsole({ logs, height = 220 }: Props) {
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  return (
    <div
      style={{
        backgroundColor: '#1a1a2e',
        borderRadius: 10,
        border: '1px solid #1e2a3a',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '8px 16px',
          backgroundColor: '#111820',
          borderBottom: '1px solid #1e2a3a',
          color: '#6ee7a8',
          fontSize: 12,
          fontWeight: 600,
          fontFamily: 'Consolas, Menlo, monospace',
        }}
      >
        ● 实时日志
      </div>
      <div
        ref={bodyRef}
        style={{
          height,
          overflowY: 'auto',
          padding: '8px 16px',
          fontFamily: 'Consolas, Menlo, monospace',
          fontSize: 12,
          lineHeight: 1.7,
        }}
      >
        {logs.map((l, i) => (
          <div key={i} style={{ display: 'flex', gap: 8 }}>
            <span style={{ color: '#5a6b7b', flexShrink: 0 }}>{l.time}</span>
            <span style={{ color: levelColor[l.level], flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {l.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
