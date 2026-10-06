import { useEffect, useRef, useState } from 'react';
import cytoscape, { type Core, type EventObject } from 'cytoscape';
import dagre from 'cytoscape-dagre';
import type { RequirementTree, NodeStatus } from '../../types';

cytoscape.use(dagre);

function statusColor(s: NodeStatus): string {
  switch (s) {
    case 'PASSED':
      return '#2ecc71';
    case 'FAILED':
      return '#e74c3c';
    case 'DESIGNING':
    case 'IMPLEMENTING':
      return '#1677ff';
    default:
      return '#64748b';
  }
}

function statusBorder(s: NodeStatus): string {
  if (s === 'DESIGNING' || s === 'IMPLEMENTING') return '#4ea1ff';
  if (s === 'PASSED') return '#6ee7a0';
  if (s === 'FAILED') return '#ff8a80';
  return '#3a506b';
}

interface Props {
  tree: RequirementTree | null;
  onNodeClick?: (nodeId: string) => void;
  height?: number | string;
}

interface TipState {
  x: number;
  y: number;
  id: string;
  name: string;
  desc: string;
}

export default function RequirementTree({ tree, onNodeClick, height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const clickRef = useRef(onNodeClick);
  clickRef.current = onNodeClick;
  const [tip, setTip] = useState<TipState | null>(null);

  // 初始化 cytoscape 实例（只一次）
  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      style: [],
      minZoom: 0.3,
      maxZoom: 2.5,
      wheelSensitivity: 0.25,
    });
    cy.on('tap', 'node', (evt: EventObject) => {
      const id = evt.target.id();
      clickRef.current?.(id);
    });
    cy.on('mouseover', 'node', (evt: EventObject) => {
      const data = evt.target.data();
      setTip({
        x: evt.renderedPosition?.x ?? 0,
        y: evt.renderedPosition?.y ?? 0,
        id: data.id,
        name: data.fullName as string,
        desc: data.desc as string,
      });
    });
    cy.on('mouseout', 'node', () => setTip(null));
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  // tree 变化时重建元素并布局
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !tree) return;

    const nodes = tree.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.id,
        fullName: n.name,
        desc: n.desc,
        status: n.status,
      },
    }));
    const edges = tree.nodes
      .filter((n) => n.parent)
      .map((n) => ({
        data: { id: `e-${n.id}`, source: n.parent as string, target: n.id },
      }));

    cy.elements().remove();
    cy.add(nodes);
    cy.add(edges);

    cy.style([
      {
        selector: 'node',
        style: {
          'background-color': (ele) => statusColor(ele.data('status') as NodeStatus),
          'border-color': (ele) => statusBorder(ele.data('status') as NodeStatus),
          label: 'data(label)',
          color: '#ffffff',
          'text-valign': 'center',
          'text-halign': 'center',
          'text-outline-width': 0,
          shape: 'round-rectangle',
          'font-size': 13,
          'font-weight': 600,
          'padding-left': '14px',
          'padding-right': '14px',
          'padding-top': '10px',
          'padding-bottom': '10px',
          'border-width': 2,
          width: 200,
          height: 'label',
        },
      },
      {
        selector: 'node:selected',
        style: { 'border-color': '#ffffff', 'border-width': 3 },
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'line-color': '#3a506b',
          'target-arrow-color': '#5a7ba0',
          'target-arrow-shape': 'triangle',
          'arrow-scale': 1.1,
          width: 1.5,
        },
      },
    ]);

    try {
      const layout = cy.layout({
        name: 'dagre',
        rankDir: 'LR',
        padding: 30,
        nodeSep: 30,
        rankSep: 50,
        nodeDimensionsIncludeLabels: true,
        animate: false,
      } as never);
      layout.one('layoutstop', () => cy.fit(undefined, 40));
      layout.run();
    } catch {
      cy.fit(undefined, 40);
    }
    setTimeout(() => cy.fit(undefined, 40), 300);
  }, [tree]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height,
        backgroundColor: '#0d1b2a',
        borderRadius: 12,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {tip && (
        <div
          style={{
            position: 'absolute',
            left: Math.min(tip.x + 14, (containerRef.current?.clientWidth ?? 400) - 240),
            top: Math.max(tip.y - 10, 8),
            zIndex: 10,
            background: 'rgba(13,27,42,.96)',
            border: '1px solid rgba(78,161,255,.4)',
            borderRadius: 8,
            padding: '8px 12px',
            maxWidth: 230,
            pointerEvents: 'none',
            color: '#cfe1f5',
            fontSize: 12,
            boxShadow: '0 4px 20px rgba(0,0,0,.4)',
          }}
        >
          <div style={{ color: '#fff', fontWeight: 600, marginBottom: 4 }}>
            {tip.id} · {tip.name}
          </div>
          <div style={{ color: '#8aa4c0' }}>{tip.desc}</div>
        </div>
      )}
    </div>
  );
}
