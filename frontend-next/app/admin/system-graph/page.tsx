'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType,
    Handle,
    Position,
    type Node,
    type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import api from '@/lib/api';
import { getApiUrl } from '@/lib/config';
import toast from 'react-hot-toast';
import {
    RefreshCw, Loader2, AlertTriangle, CheckCircle, XCircle, Info, X,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────
interface GraphNode {
    id: string;
    label: string;
    group: string;
    icon: string;
    count: number;
    breakdown: Record<string, any>;
    health: 'healthy' | 'warning' | 'error';
}

interface GraphEdge {
    from: string;
    to: string;
    label: string;
    count: number;
}

interface Warning {
    level: 'error' | 'warning' | 'info';
    message: string;
}

// ── Color Theme ────────────────────────────────────────────────────
const GROUP_COLORS: Record<string, { bg: string; border: string; text: string; glow: string }> = {
    sources: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700', glow: 'shadow-red-200' },
    content: { bg: 'bg-emerald-50', border: 'border-emerald-300', text: 'text-emerald-700', glow: 'shadow-emerald-200' },
    vehicles: { bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-700', glow: 'shadow-blue-200' },
    taxonomy: { bg: 'bg-purple-50', border: 'border-purple-300', text: 'text-purple-700', glow: 'shadow-purple-200' },
    interactions: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700', glow: 'shadow-amber-200' },
    ml: { bg: 'bg-indigo-50', border: 'border-indigo-300', text: 'text-indigo-700', glow: 'shadow-indigo-200' },
    system: { bg: 'bg-gray-50', border: 'border-gray-300', text: 'text-gray-700', glow: 'shadow-gray-200' },
};

const HEALTH_DOT: Record<string, string> = {
    healthy: 'bg-emerald-500',
    warning: 'bg-amber-500 animate-pulse',
    error: 'bg-red-500 animate-pulse',
};

// ── Custom Node Component ──────────────────────────────────────────
function EntityNode({ data }: { data: any }) {
    const colors = GROUP_COLORS[data.group] || GROUP_COLORS.system;
    const isSelected = data.isSelected;

    return (
        <div
            className={`relative px-4 py-3 rounded-xl border-2 shadow-lg transition-all duration-200 cursor-pointer min-w-[140px]
                ${colors.bg} ${colors.border} ${isSelected ? `ring-2 ring-offset-2 ring-indigo-400 ${colors.glow} shadow-xl scale-105` : 'hover:shadow-xl hover:scale-[1.02]'}`}
            onClick={() => data.onSelect?.(data.nodeData)}
        >
            <Handle type="target" position={Position.Left} className="!bg-gray-400 !w-2 !h-2 !border-0" />
            <Handle type="source" position={Position.Right} className="!bg-gray-400 !w-2 !h-2 !border-0" />

            {/* Health dot */}
            <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${HEALTH_DOT[data.health]} border-2 border-white`} />

            {/* Icon + Label */}
            <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">{data.icon}</span>
                <span className={`text-xs font-bold ${colors.text} uppercase tracking-wider`}>{data.label}</span>
            </div>

            {/* Count */}
            <div className="text-2xl font-black text-gray-900 leading-none">
                {data.count.toLocaleString()}
            </div>

            {/* Group Label */}
            <div className="text-[9px] text-gray-400 font-semibold uppercase tracking-widest mt-1">
                {data.group}
            </div>
        </div>
    );
}

const nodeTypes = { entity: EntityNode };

// ── Layout ─────────────────────────────────────────────────────────
// Manual positions for clean dagre-like layout
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
    // Sources (left column)
    rss_feeds: { x: 50, y: 60 },
    rss_items: { x: 280, y: 60 },
    youtube: { x: 50, y: 200 },
    // Content (middle)
    pending_articles: { x: 520, y: 60 },
    articles: { x: 760, y: 60 },
    article_images: { x: 760, y: 200 },
    // Vehicles (right column)
    brands: { x: 1000, y: 60 },
    brand_aliases: { x: 1000, y: 200 },
    car_specs: { x: 1000, y: 340 },
    vehicle_specs: { x: 1000, y: 480 },
    // Taxonomy (bottom-middle)
    categories: { x: 520, y: 350 },
    tag_groups: { x: 520, y: 490 },
    tags: { x: 760, y: 350 },
    // Interactions (bottom-left)
    comments: { x: 50, y: 380 },
    ratings: { x: 280, y: 380 },
    favorites: { x: 50, y: 520 },
    feedback: { x: 280, y: 520 },
    // ML (top-right)
    embeddings: { x: 760, y: 490 },
    ab_tests: { x: 520, y: 200 },
    // System (far right bottom)
    subscribers: { x: 280, y: 200 },
    errors: { x: 50, y: 660 },
};

// ── Edge Styles ────────────────────────────────────────────────────
const EDGE_STYLE = {
    stroke: '#94a3b8',
    strokeWidth: 1.5,
};

const ANIMATED_EDGE_STYLE = {
    stroke: '#6366f1',
    strokeWidth: 2,
};

// ── Main Component ─────────────────────────────────────────────────
export default function SystemGraphPage() {
    const [graphData, setGraphData] = useState<{
        nodes: GraphNode[];
        edges: GraphEdge[];
        warnings: Warning[];
    } | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const apiUrl = getApiUrl();

    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

    const loadData = useCallback(async (silent = false) => {
        if (!silent) setLoading(true);
        try {
            const { data } = await api.get(`${apiUrl}/health/graph-data/`);
            setGraphData(data);

            // Build React Flow nodes
            const rfNodes: Node[] = data.nodes.map((n: GraphNode) => ({
                id: n.id,
                type: 'entity',
                position: NODE_POSITIONS[n.id] || { x: 600, y: 300 },
                data: {
                    ...n,
                    nodeData: n,
                    isSelected: selectedNode?.id === n.id,
                    onSelect: (nd: GraphNode) => setSelectedNode(prev => prev?.id === nd.id ? null : nd),
                },
            }));

            // Build React Flow edges
            const rfEdges: Edge[] = data.edges.map((e: GraphEdge, i: number) => ({
                id: `e-${i}`,
                source: e.from,
                target: e.to,
                label: e.count > 0 ? `${e.label} (${e.count})` : e.label,
                type: 'default',
                animated: e.count > 100,
                style: e.count > 100 ? ANIMATED_EDGE_STYLE : EDGE_STYLE,
                labelStyle: { fontSize: 10, fontWeight: 600, fill: '#64748b' },
                labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.9 },
                labelBgPadding: [4, 2] as [number, number],
                markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8', width: 16, height: 16 },
            }));

            setNodes(rfNodes);
            setEdges(rfEdges);
        } catch (err) {
            console.error('Failed to load graph data:', err);
            if (!silent) toast.error('Failed to load system graph');
        } finally {
            setLoading(false);
        }
    }, [apiUrl, selectedNode?.id]);

    useEffect(() => { loadData(); }, []);

    // Update node selection highlighting when selectedNode changes
    useEffect(() => {
        if (!graphData) return;
        setNodes((prev: Node[]) => prev.map(n => ({
            ...n,
            data: {
                ...(n.data as Record<string, any>),
                isSelected: selectedNode?.id === (n.data as any).nodeData?.id,
                onSelect: (nd: GraphNode) => setSelectedNode((p: GraphNode | null) => p?.id === nd.id ? null : nd),
            },
        })));
    }, [selectedNode?.id]);

    // ── Warning Badge ──────────────────────────────────────────────
    const WarningBadge = ({ w }: { w: Warning }) => {
        const cfg: Record<string, { icon: any; color: string }> = {
            error: { icon: <XCircle className="w-4 h-4" />, color: 'bg-red-50 text-red-700 border-red-200' },
            warning: { icon: <AlertTriangle className="w-4 h-4" />, color: 'bg-amber-50 text-amber-700 border-amber-200' },
            info: { icon: <Info className="w-4 h-4" />, color: 'bg-blue-50 text-blue-700 border-blue-200' },
        };
        const c = cfg[w.level] || cfg.info;
        return (
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium ${c.color}`}>
                {c.icon}
                {w.message}
            </div>
        );
    };

    // ── Render ──────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-3" />
                    <p className="text-gray-600 font-medium">Loading system graph...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-120px)]">
            {/* Header */}
            <div className="flex items-center justify-between mb-4 px-1">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950 flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                                className="text-white">
                                <circle cx="12" cy="12" r="3" /><line x1="12" y1="1" x2="12" y2="4" /><line x1="12" y1="20" x2="12" y2="23" />
                                <line x1="4.22" y1="4.22" x2="6.34" y2="6.34" /><line x1="17.66" y1="17.66" x2="19.78" y2="19.78" />
                                <line x1="1" y1="12" x2="4" y2="12" /><line x1="20" y1="12" x2="23" y2="12" />
                                <line x1="4.22" y1="19.78" x2="6.34" y2="17.66" /><line x1="17.66" y1="6.34" x2="19.78" y2="4.22" />
                            </svg>
                        </div>
                        System Graph
                    </h1>
                    <p className="text-sm text-gray-600 mt-1">
                        Interactive entity map · {graphData?.nodes.length || 0} nodes · {graphData?.edges.length || 0} connections
                    </p>
                </div>
                <button
                    onClick={() => { setLoading(true); loadData(); }}
                    className="px-4 py-2 rounded-xl bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm font-semibold border border-gray-200 transition flex items-center gap-2"
                >
                    <RefreshCw className="w-4 h-4" /> Refresh
                </button>
            </div>

            {/* Warnings */}
            {graphData?.warnings && graphData.warnings.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4 px-1">
                    {graphData.warnings.map((w, i) => <WarningBadge key={i} w={w} />)}
                </div>
            )}

            {/* Legend */}
            <div className="flex flex-wrap gap-3 mb-3 px-1 text-[11px]">
                {Object.entries(GROUP_COLORS).map(([group, c]) => (
                    <span key={group} className={`flex items-center gap-1.5 px-2 py-1 rounded-md border ${c.bg} ${c.border} ${c.text} font-semibold uppercase tracking-wider`}>
                        <span className={`w-2 h-2 rounded-full ${c.border.replace('border-', 'bg-')}`} />
                        {group}
                    </span>
                ))}
                <span className="flex items-center gap-2 text-gray-500 font-medium ml-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Healthy
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Warning
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Error
                </span>
            </div>

            {/* Graph + Sidebar */}
            <div className="flex-1 flex gap-4 min-h-0">
                {/* React Flow Canvas */}
                <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        nodeTypes={nodeTypes}
                        fitView
                        fitViewOptions={{ padding: 0.3 }}
                        minZoom={0.3}
                        maxZoom={2}
                        proOptions={{ hideAttribution: true }}
                    >
                        <Background color="#e2e8f0" gap={20} size={1} />
                        <Controls showInteractive={false} />
                        <MiniMap
                            nodeStrokeWidth={3}
                            pannable
                            zoomable
                            style={{ background: '#f8fafc' }}
                        />
                    </ReactFlow>
                </div>

                {/* Detail Sidebar */}
                {selectedNode && (
                    <div className="w-80 shrink-0 bg-white rounded-xl border border-gray-200 shadow-sm p-5 overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <span className="text-2xl">{selectedNode.icon}</span>
                                <h2 className="text-lg font-black text-gray-900">{selectedNode.label}</h2>
                            </div>
                            <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-gray-600">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Health */}
                        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg mb-4 ${selectedNode.health === 'healthy' ? 'bg-emerald-50 text-emerald-700' :
                            selectedNode.health === 'warning' ? 'bg-amber-50 text-amber-700' :
                                'bg-red-50 text-red-700'
                            }`}>
                            {selectedNode.health === 'healthy' ? <CheckCircle className="w-4 h-4" /> :
                                selectedNode.health === 'warning' ? <AlertTriangle className="w-4 h-4" /> :
                                    <XCircle className="w-4 h-4" />}
                            <span className="text-sm font-semibold capitalize">{selectedNode.health}</span>
                        </div>

                        {/* Count */}
                        <div className="bg-gray-50 rounded-lg p-4 mb-4 text-center">
                            <p className="text-4xl font-black text-gray-900">{selectedNode.count.toLocaleString()}</p>
                            <p className="text-xs text-gray-500 font-medium mt-1">Total Records</p>
                        </div>

                        {/* Breakdown */}
                        {Object.keys(selectedNode.breakdown).length > 0 && (
                            <div>
                                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Breakdown</h3>
                                <div className="space-y-2">
                                    {Object.entries(selectedNode.breakdown).map(([key, val]) => (
                                        <div key={key} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg">
                                            <span className="text-sm text-gray-600 capitalize font-medium">{key.replace(/_/g, ' ')}</span>
                                            <span className="text-sm font-bold text-gray-900">
                                                {typeof val === 'number' ? val.toLocaleString() : val}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Connected edges */}
                        <div className="mt-4">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Connections</h3>
                            <div className="space-y-1.5">
                                {graphData?.edges
                                    .filter(e => e.from === selectedNode.id || e.to === selectedNode.id)
                                    .map((e, i) => {
                                        const isOutgoing = e.from === selectedNode.id;
                                        const otherNode = graphData.nodes.find(n => n.id === (isOutgoing ? e.to : e.from));
                                        return (
                                            <div key={i}
                                                className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-sm cursor-pointer hover:bg-indigo-50 transition"
                                                onClick={() => otherNode && setSelectedNode(otherNode)}
                                            >
                                                <span className="text-gray-400">{isOutgoing ? '→' : '←'}</span>
                                                <span className="font-medium text-gray-700">{otherNode?.icon} {otherNode?.label}</span>
                                                <span className="ml-auto text-xs text-gray-400 font-mono">
                                                    {e.label} {e.count > 0 ? `(${e.count})` : ''}
                                                </span>
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>

                        {/* Group */}
                        <div className="mt-4 pt-4 border-t border-gray-100">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[10px] font-bold uppercase tracking-wider
                                ${GROUP_COLORS[selectedNode.group]?.bg || ''} ${GROUP_COLORS[selectedNode.group]?.border || ''} ${GROUP_COLORS[selectedNode.group]?.text || ''}`}>
                                {selectedNode.group}
                            </span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
