import { useCallback, useEffect, useMemo, useState } from "react";
import dagre from "dagre";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Panel,
  Position,
  ReactFlow,
} from "@xyflow/react";

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const NODE_DIMENSIONS = {
  focus: { width: 260, height: 92 },
  shape: { width: 250, height: 94 },
  leaf: { width: 210, height: 88 },
};

const SHAPE_LEVEL_CLASS = {
  1: "shape-level-1",
  2: "shape-level-2",
  3: "shape-level-3",
  4: "shape-level-4",
  5: "shape-level-5",
  6: "shape-level-6",
};

function shortIri(value) {
  if (!value) return "";
  if (value.startsWith("http://") || value.startsWith("https://")) {
    const trimmed = value.replace(/^https?:\/\//, "").replace(/[<>]/g, "");
    const parts = trimmed.split("/");
    return parts[parts.length - 1] || trimmed;
  }
  if (value.includes(":")) return value.split(":").pop();
  return value;
}

function shortComponent(component) {
  const local = shortIri(component);
  return local.replace(/ConstraintComponent$/, "");
}

function issueLabel(node) {
  const path = shortIri(node.path || "constraint");
  const component = shortComponent(node.component || "");
  if (component === "MinCount") return `missing ${path}`;
  if (component === "MaxCount") return `too many ${path}`;
  if (component === "Datatype") return `invalid datatype on ${path}`;
  if (component === "Pattern") return `pattern mismatch on ${path}`;
  return `${component || "violation"} on ${path}`;
}

function collectLeafEntries(nodes, acc = []) {
  (nodes || []).forEach((node) => {
    if (!node) return;
    if (node.type === "leaf") {
      acc.push({ node, issue: issueLabel(node) });
      return;
    }
    collectLeafEntries(node.children || [], acc);
  });
  return acc;
}

function graphLeafId(entry, index) {
  return `leaf|${entry.node.focusNode}|${entry.node.path || ""}|${entry.node.component || ""}|${entry.node.value || ""}|${index}`;
}

function buildFocusGraph(entries, focusLabel) {
  const root = {
    id: `focus|${focusLabel}`,
    type: "focus",
    label: focusLabel,
    raw: focusLabel,
    depth: 0,
    children: [],
    childMap: new Map(),
  };

  entries.forEach((entry, index) => {
    const chain = entry.node.refChain || [];
    let parent = root;

    chain.forEach((shape, shapeIndex) => {
      const key = `shape|${chain.slice(0, shapeIndex + 1).join("->")}`;
      let next = parent.childMap.get(key);
      if (!next) {
        next = {
          id: key,
          type: "shape",
          label: shape,
          raw: shape,
          depth: shapeIndex + 1,
          entryCount: 0,
          children: [],
          childMap: new Map(),
        };
        parent.childMap.set(key, next);
        parent.children.push(next);
      }
      next.entryCount += 1;
      parent = next;
    });

    parent.children.push({
      id: graphLeafId(entry, index),
      type: "leaf",
      label: entry.node.path || entry.issue,
      raw: entry.node.path || entry.issue,
      issue: entry.issue,
      path: entry.node.path || "",
      component: entry.node.component || "",
      value: entry.node.value || "",
      message: entry.node.message || "",
      repairHint: entry.node.repairHint || "",
      fullChain: chain,
      entry,
      depth: chain.length + 1,
      status: "fail",
    });
  });

  function finalize(node) {
    delete node.childMap;
    node.children = (node.children || []).sort((a, b) => {
      if (a.type !== b.type) return a.type === "shape" ? -1 : 1;
      return String(a.label).localeCompare(String(b.label));
    });
    node.children.forEach(finalize);
    return node;
  }

  return finalize(root);
}

function indexGraph(root) {
  const map = new Map();
  const walk = (node, parent = null) => {
    map.set(node.id, { node, parent });
    (node.children || []).forEach((child) => walk(child, node));
  };
  walk(root, null);
  return map;
}

function edgeLabel(parent, child) {
  if (!parent) return "";
  if (parent.type === "focus") return "does not conform to";
  if (child.type === "shape") return "is referencing";
  return "violates";
}

function getLayoutedElements(nodes, edges) {
  dagreGraph.setGraph({
    rankdir: "TB",
    align: "UL",
    ranksep: 100,
    nodesep: 44,
    marginx: 24,
    marginy: 24,
  });

  nodes.forEach((node) => {
    const dims = NODE_DIMENSIONS[node.data.kind] || NODE_DIMENSIONS.shape;
    dagreGraph.setNode(node.id, dims);
  });

  edges.forEach((edge) => dagreGraph.setEdge(edge.source, edge.target));
  dagre.layout(dagreGraph);

  return {
    nodes: nodes.map((node) => {
      const dims = NODE_DIMENSIONS[node.data.kind] || NODE_DIMENSIONS.shape;
      const positioned = dagreGraph.node(node.id);
      return {
        ...node,
        position: {
          x: positioned.x - dims.width / 2,
          y: positioned.y - dims.height / 2,
        },
      };
    }),
    edges,
  };
}

function GraphCardNode({ data }) {
  const badge =
    data.kind === "shape" ? (
      <span className="rf-depth-badge">{`L${data.depth}`}</span>
    ) : null;

  return (
    <>
      <Handle type="target" position={Position.Top} className="rf-handle" />
      <button
        type="button"
        className={`rf-node rf-${data.kind} ${data.levelClass || ""} ${
          data.expanded ? "is-expanded" : ""
        } ${data.selected ? "is-selected" : ""}`}
        onClick={() => data.onPress(data.id)}
      >
        <div className="rf-node-main">
          <span className="rf-node-label" title={data.raw}>
            {data.displayLabel}
          </span>
          {badge}
        </div>
        {data.kind === "shape" ? (
          <span className="rf-node-meta">
            {data.entryCount} failure{data.entryCount === 1 ? "" : "s"}
            {data.childCount ? ` · ${data.childCount} child${data.childCount === 1 ? "" : "ren"}` : ""}
          </span>
        ) : null}
        {data.kind === "leaf" && data.value ? (
          <span className="rf-leaf-value" title={String(data.value)}>
            {String(data.value)}
          </span>
        ) : null}
      </button>
      <Handle type="source" position={Position.Bottom} className="rf-handle" />
    </>
  );
}

const nodeTypes = {
  focus: GraphCardNode,
  shape: GraphCardNode,
  leaf: GraphCardNode,
};

function detailForNode(record, focusLabel) {
  const { node, parent } = record;
  if (node.type === "focus") {
    return {
      title: shortIri(node.label),
      subtitle: node.label,
      paragraphs: [
        `${shortIri(node.label)} is the violated focus node.`,
        "Expand the graph by clicking shape cards to reveal nested referencing failures.",
      ],
    };
  }

  if (node.type === "shape") {
    const intro =
      node.depth === 1
        ? `${shortIri(focusLabel)} does not conform to ${shortIri(node.label)}.`
        : `${shortIri(node.label)} is ${node.depth} levels deep in the current failure chain.`;
    const childShapes = (node.children || [])
      .filter((child) => child.type === "shape")
      .map((child) => shortIri(child.label));
    const childLeaves = (node.children || [])
      .filter((child) => child.type === "leaf")
      .map((child) => shortIri(child.label));
    return {
      title: shortIri(node.label),
      subtitle: node.label,
      paragraphs: [
        intro,
        `${node.entryCount || childLeaves.length} violating leaves are currently reachable from this shape.`,
      ],
      bullets: [
        childShapes.length ? `References ${childShapes.join(", ")}` : null,
        childLeaves.length ? `Violates ${childLeaves.join(", ")}` : null,
      ].filter(Boolean),
    };
  }

  return {
    title: shortIri(node.path || node.label),
    subtitle: node.component ? `${shortComponent(node.component)} constraint` : "Leaf failure",
    paragraphs: [
      node.message || issueLabel(node),
      node.repairHint || "No repair hint was generated for this leaf.",
    ],
    bullets: [
      `Reached from ${shortIri(focusLabel)}`,
      parent?.label ? `Parent shape ${shortIri(parent.label)}` : null,
      node.path ? `Path ${node.path}` : null,
      node.value ? `Observed value ${node.value}` : null,
      node.fullChain?.length
        ? `Reference chain ${node.fullChain.map(shortIri).join(" -> ")}`
        : "Direct leaf violation",
    ].filter(Boolean),
  };
}

function App() {
  const [reportData, setReportData] = useState([]);
  const [error, setError] = useState("");
  const [selectedFocus, setSelectedFocus] = useState("");
  const [expandedIds, setExpandedIds] = useState(() => new Set());
  const [selectedNodeId, setSelectedNodeId] = useState("");

  useEffect(() => {
    let alive = true;
    fetch("/tc6_explanation.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Could not load tc6_explanation.json (${response.status})`);
        }
        return response.json();
      })
      .then((data) => {
        if (!alive) return;
        setReportData(data);
        const focus = data[0]?.focusNode || data[0]?.focus_node || "";
        setSelectedFocus(focus);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err.message || "Unknown loading error");
      });
    return () => {
      alive = false;
    };
  }, []);

  const groupedByFocus = useMemo(() => {
    const groups = new Map();
    reportData.forEach((node) => {
      const key = node.focusNode || node.focus_node || "unknown";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    });
    return groups;
  }, [reportData]);

  const focusOptions = useMemo(() => Array.from(groupedByFocus.keys()), [groupedByFocus]);

  const selectedGraph = useMemo(() => {
    if (!selectedFocus) return null;
    const roots = groupedByFocus.get(selectedFocus) || [];
    const entries = collectLeafEntries(roots);
    if (!entries.length) return null;
    return buildFocusGraph(entries, selectedFocus);
  }, [groupedByFocus, selectedFocus]);

  const graphIndex = useMemo(
    () => (selectedGraph ? indexGraph(selectedGraph) : new Map()),
    [selectedGraph],
  );

  useEffect(() => {
    if (!selectedGraph) return;
    setExpandedIds(new Set([selectedGraph.id]));
    setSelectedNodeId(selectedGraph.id);
  }, [selectedGraph]);

  const onPressNode = useCallback(
    (nodeId) => {
      setSelectedNodeId(nodeId);
      setExpandedIds((current) => {
        const next = new Set(current);
        const record = graphIndex.get(nodeId);
        if (record?.node?.children?.length) {
          if (next.has(nodeId)) next.delete(nodeId);
          else next.add(nodeId);
        }
        return next;
      });
    },
    [graphIndex],
  );

  const flowElements = useMemo(() => {
    if (!selectedGraph) return { nodes: [], edges: [] };

    const nodes = [];
    const edges = [];

    const walk = (node, parent = null) => {
      const isExpanded = expandedIds.has(node.id);
      const childCount = (node.children || []).length;
      const nodeKind = node.type === "focus" ? "focus" : node.type === "leaf" ? "leaf" : "shape";
      const nodeData = {
        id: node.id,
        kind: nodeKind,
        label: node.label,
        raw: node.raw || node.label,
        depth: node.depth || 0,
        displayLabel: shortIri(node.label),
        entryCount: node.entryCount || 0,
        childCount,
        value: node.value || "",
        levelClass:
          nodeKind === "shape"
            ? SHAPE_LEVEL_CLASS[Math.min(node.depth || 1, 6)] || SHAPE_LEVEL_CLASS[6]
            : "",
        expanded: isExpanded,
        selected: node.id === selectedNodeId,
        onPress: onPressNode,
      };

      nodes.push({
        id: node.id,
        type: nodeKind,
        data: nodeData,
        position: { x: 0, y: 0 },
        draggable: false,
        selectable: false,
        connectable: false,
      });

      if (parent) {
        edges.push({
          id: `${parent.id}->${node.id}`,
          source: parent.id,
          target: node.id,
          type: "smoothstep",
          animated: false,
          label: edgeLabel(parent, node),
          labelStyle: { fill: "#cbd5e1", fontSize: 12, fontStyle: "italic" },
          style: { stroke: "rgba(148, 163, 184, 0.7)", strokeWidth: 1.4 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(148, 163, 184, 0.7)" },
        });
      }

      if (childCount && expandedIds.has(node.id)) {
        node.children.forEach((child) => walk(child, node));
      }
    };

    walk(selectedGraph, null);
    return getLayoutedElements(nodes, edges);
  }, [expandedIds, onPressNode, selectedGraph, selectedNodeId]);

  const detail = useMemo(() => {
    if (!selectedGraph) return null;
    const record = graphIndex.get(selectedNodeId) || { node: selectedGraph, parent: null };
    return detailForNode(record, selectedFocus);
  }, [graphIndex, selectedGraph, selectedFocus, selectedNodeId]);

  if (error) {
    return <div className="rf-page"><div className="rf-error">{error}</div></div>;
  }

  return (
    <div className="rf-page">
      <aside className="rf-sidebar">
        <div className="rf-sidebar-section">
          <p className="rf-eyebrow">React Flow Prototype</p>
          <h1>Expandable SHACL graph</h1>
          <p className="rf-copy">
            This prototype uses the real tc6 explanation JSON and renders only the visible branch of the graph.
          </p>
        </div>

        <div className="rf-sidebar-section">
          <label className="rf-label" htmlFor="focus-select">Focus node</label>
          <select
            id="focus-select"
            className="rf-select"
            value={selectedFocus}
            onChange={(event) => setSelectedFocus(event.target.value)}
          >
            {focusOptions.map((focus) => (
              <option key={focus} value={focus}>
                {focus}
              </option>
            ))}
          </select>
        </div>

        <div className="rf-sidebar-section">
          <div className="rf-actions">
            <button
              type="button"
              className="rf-action-btn"
              onClick={() => selectedGraph && setExpandedIds(new Set([selectedGraph.id]))}
            >
              collapse to root
            </button>
            <button
              type="button"
              className="rf-action-btn"
              onClick={() => {
                if (!selectedGraph) return;
                const all = new Set();
                graphIndex.forEach((_value, key) => all.add(key));
                setExpandedIds(all);
              }}
            >
              expand all visible
            </button>
          </div>
        </div>

        {detail ? (
          <div className="rf-sidebar-section rf-detail-card">
            <p className="rf-eyebrow">Selected node</p>
            <h2>{detail.title}</h2>
            <p className="rf-subtle">{detail.subtitle}</p>
            {detail.paragraphs.map((paragraph) => (
              <p key={paragraph} className="rf-copy">{paragraph}</p>
            ))}
            {detail.bullets?.length ? (
              <ul className="rf-list">
                {detail.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}
              </ul>
            ) : null}
          </div>
        ) : null}
      </aside>

      <main className="rf-main">
        <div className="rf-canvas-shell">
          <ReactFlow
            nodes={flowElements.nodes}
            edges={flowElements.edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.25 }}
            onlyRenderVisibleElements
            panOnDrag
            zoomOnScroll
            zoomOnPinch
            zoomOnDoubleClick={false}
            minZoom={0.2}
            maxZoom={2.2}
            proOptions={{ hideAttribution: true }}
          >
            <MiniMap
              pannable
              zoomable
              nodeColor={(node) => {
                if (node.type === "focus") return "#ff7f41";
                if (node.type === "leaf") return "#ff4f6d";
                if (node.data.depth === 1) return "#60a5fa";
                if (node.data.depth === 2) return "#a78bfa";
                if (node.data.depth === 3) return "#8fd14f";
                if (node.data.depth === 4) return "#4fd1c5";
                if (node.data.depth === 5) return "#fbbf24";
                return "#94a3b8";
              }}
            />
            <Controls showInteractive />
            <Background color="rgba(148, 163, 184, 0.18)" gap={24} />
            <Panel position="top-left" className="rf-panel">
              <strong>{shortIri(selectedFocus || "focus")}</strong>
              <span>{flowElements.nodes.length} visible nodes</span>
            </Panel>
          </ReactFlow>
        </div>
      </main>
    </div>
  );
}

export default App;
