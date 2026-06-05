import React, { useState, useEffect, useRef } from 'https://esm.sh/react@18.2.0';
import htm from 'https://esm.sh/htm@3.1.1';

const html = htm.bind(React.createElement);

// Direct inline SVGs for Lucide Icons to prevent React DOM mutation conflicts
const Icons = {
    ShieldAlert: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 13c0 5-3.5 7.5-7.66 9.7a1 1 0 0 1-.68 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 .76-.97l8-2a1 1 0 0 1 .48 0l8 2A1 1 0 0 1 20 6z"/>
            <path d="M12 8v4"/>
            <path d="M12 16h.01"/>
        </svg>
    `,
    Play: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="6 3 20 12 6 21 6 3"/>
        </svg>
    `,
    BarChart: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
    `,
    Activity: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
    `,
    Terminal: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="4 17 10 11 4 5"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
        </svg>
    `,
    Network: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="16" y="16" width="6" height="6" rx="1"/>
            <rect x="2" y="16" width="6" height="6" rx="1"/>
            <rect x="9" y="2" width="6" height="6" rx="1"/>
            <path d="M12 8v4"/>
            <path d="M12 12H5v4"/>
            <path d="M12 12h7v4"/>
        </svg>
    `,
    GitPullRequest: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="18" cy="18" r="3"/>
            <circle cx="6" cy="6" r="3"/>
            <circle cx="6" cy="18" r="3"/>
            <path d="M18 15V9a4 4 0 0 0-4-4H9"/>
            <line x1="6" y1="9" x2="6" y2="15"/>
        </svg>
    `,
    AlertTriangle: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
    `,
    FileCode: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
            <polyline points="14 2 14 8 20 8"/>
            <polyline points="8 13 6 15 8 17"/>
            <polyline points="16 13 18 15 16 17"/>
            <line x1="12" y1="13" x2="10" y2="17"/>
        </svg>
    `,
    X: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
    `,
    XCircle: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
    `,
    Clock: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
        </svg>
    `,
    Trash: () => html`
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            <line x1="10" y1="11" x2="10" y2="17"/>
            <line x1="14" y1="11" x2="14" y2="17"/>
        </svg>
    `
};

export default function App() {
    const [repoUrl, setRepoUrl] = useState('https://github.com/pallets/flask');
    const [base, setBase] = useState('2.3.0');
    const [head, setHead] = useState('3.0.0');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [activeTab, setActiveTab] = useState('summary'); // 'summary' or 'history'
    const [history, setHistory] = useState([]);

    const containerRef = useRef(null);
    const cyRef = useRef(null);

    // Load history from localStorage on mount
    useEffect(() => {
        const storedHistory = localStorage.getItem('diff_guard_history');
        if (storedHistory) {
            try {
                setHistory(JSON.parse(storedHistory));
            } catch (e) {
                console.error("Error parsing history from localStorage", e);
            }
        }
    }, []);

    const saveToHistory = (url, b, h, result) => {
        let repoName = url;
        try {
            const cleanUrl = url.trim().replace(/\.git$/, '');
            if (cleanUrl.includes('github.com/')) {
                const parts = cleanUrl.split('github.com/');
                if (parts.length > 1) repoName = parts[1];
            } else if (cleanUrl.includes('github.com:')) {
                const parts = cleanUrl.split('github.com:');
                if (parts.length > 1) repoName = parts[1];
            }
        } catch (e) {}

        const newItem = {
            id: Date.now().toString(),
            repoUrl: url,
            repoName: repoName,
            base: b,
            head: h,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            score: result.risk_score,
            status: result.status,
            result: result
        };

        // Prepend and dedup checks on the exact same repo/base/head coordinates
        const filtered = history.filter(item => !(item.repoUrl === url && item.base === b && item.head === h));
        const updatedHistory = [newItem, ...filtered].slice(0, 50); // limit to last 50 items
        setHistory(updatedHistory);
        localStorage.setItem('diff_guard_history', JSON.stringify(updatedHistory));
    };

    const deleteHistoryItem = (id, e) => {
        if (e) e.stopPropagation();
        const updated = history.filter(item => item.id !== id);
        setHistory(updated);
        localStorage.setItem('diff_guard_history', JSON.stringify(updated));
    };

    const clearAllHistory = () => {
        setHistory([]);
        localStorage.removeItem('diff_guard_history');
    };

    const loadHistoryItem = (item) => {
        setRepoUrl(item.repoUrl);
        setBase(item.base);
        setHead(item.head);
        setData(item.result);
        setSelectedNode(null);
        setActiveTab('summary'); // Switch view to display results
    };

    // Run Lucide icons renderer when DOM updates
    useEffect(() => {
        if (window.lucide) {
            window.lucide.createIcons();
        }
    });

    const handleAnalyze = async (e) => {
        if (e) e.preventDefault();
        setLoading(true);
        setError(null);
        setSelectedNode(null);
        
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    base: base,
                    head: head
                })
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Server error: ${response.statusText}`);
            }
            
            const result = await response.json();
            setData(result);
            saveToHistory(repoUrl, base, head, result);
        } catch (err) {
            console.error(err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Cytoscape initialization and graph mapping
    useEffect(() => {
        if (!data || !containerRef.current) return;

        const elements = [];
        
        // 1. Map nodes
        data.graph_data.nodes.forEach(node => {
            elements.push({
                data: {
                    id: node.id,
                    label: node.label,
                    isModified: node.is_modified,
                    isImpacted: node.is_impacted
                }
            });
        });

        // 2. Map edges
        data.graph_data.edges.forEach(edge => {
            elements.push({
                data: {
                    id: `${edge.source}-${edge.target}`,
                    source: edge.source,
                    target: edge.target
                }
            });
        });

        // 3. Initialize Cytoscape Instance
        const cy = window.cytoscape({
            container: containerRef.current,
            elements: elements,
            boxSelectionEnabled: false,
            autounselectify: true,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'background-color': '#4b5563',
                        'color': '#f3f4f6',
                        'font-size': '10px',
                        'font-family': 'Outfit, sans-serif',
                        'text-valign': 'center',
                        'text-halign': 'right',
                        'text-margin-x': 6,
                        'width': '16px',
                        'height': '16px',
                        'transition-property': 'background-color, line-color, target-arrow-color, width, height, opacity',
                        'transition-duration': '0.15s'
                    }
                },
                {
                    selector: 'node[isModified]',
                    style: {
                        'background-color': '#f59e0b',
                        'width': '22px',
                        'height': '22px',
                        'border-width': '2px',
                        'border-color': '#fbbf24',
                        'shadow-blur': '10px',
                        'shadow-color': '#f59e0b',
                        'shadow-opacity': '0.85'
                    }
                },
                {
                    selector: 'node[isImpacted]',
                    style: {
                        'background-color': '#818cf8',
                        'width': '18px',
                        'height': '18px',
                        'border-width': '1px',
                        'border-color': '#a5b4fc'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 1.5,
                        'line-color': '#374151',
                        'target-arrow-color': '#374151',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 0.8,
                        'transition-property': 'line-color, target-arrow-color, width, opacity',
                        'transition-duration': '0.15s'
                    }
                },
                {
                    selector: '.highlighted-node',
                    style: {
                        'background-color': '#ef4444',
                        'border-color': '#f87171',
                        'border-width': '3px',
                        'width': '26px',
                        'height': '26px'
                    }
                },
                {
                    selector: '.highlighted-edge',
                    style: {
                        'line-color': '#ef4444',
                        'target-arrow-color': '#ef4444',
                        'width': 3.5
                    }
                },
                {
                    selector: '.dimmed',
                    style: {
                        'opacity': 0.15
                    }
                }
            ],
            layout: {
                name: 'cose',
                idealEdgeLength: 80,
                nodeOverlap: 20,
                refresh: 20,
                fit: true,
                padding: 40,
                randomize: false,
                componentSpacing: 100,
                nodeRepulsion: 400000,
                edgeElasticity: 100,
                nestingFactor: 5,
                gravity: 80,
                numIter: 1000
            }
        });

        cyRef.current = cy;

        // Select node
        cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            setSelectedNode({
                id: node.id(),
                isModified: node.data('isModified'),
                isImpacted: node.data('isImpacted')
            });
        });

        // Hover highlighting logic
        cy.on('mouseover', 'node', (evt) => {
            const node = evt.target;
            const successors = node.successors(); // Downstream affected files
            const pathElements = successors.union(node);
            
            cy.elements().addClass('dimmed');
            pathElements.removeClass('dimmed');
            
            // Highlight connections in path
            pathElements.edgesWith(pathElements).forEach(edge => {
                edge.removeClass('dimmed');
                edge.addClass('highlighted-edge');
            });
            
            node.addClass('highlighted-node');
        });

        cy.on('mouseout', 'node', (evt) => {
            cy.elements().removeClass('dimmed');
            cy.elements().removeClass('highlighted-edge');
            evt.target.removeClass('highlighted-node');
        });

        return () => {
            cy.destroy();
        };
    }, [data]);

    // Compute circular progress properties
    const score = data ? data.risk_score : 0;
    const strokeDashoffset = 377 - (377 * score) / 100;
    const riskStatus = data ? data.status.toLowerCase() : '';
    
    // Find details for selected node
    const getSelectedNodeDetails = () => {
        if (!selectedNode || !data) return null;
        const nodeId = selectedNode.id;
        
        let details = {
            id: nodeId,
            status: selectedNode.isModified ? 'modified' : (selectedNode.isImpacted ? 'impacted' : 'neutral'),
            entities: []
        };
        
        if (selectedNode.isModified) {
            // Find in modified files list
            const modInfo = data.modified_files.find(f => f.file === nodeId);
            if (modInfo) {
                details.entities = modInfo.changed_entities.map(e => `${e.entity} (${e.change_type})`);
            }
        } else if (selectedNode.isImpacted) {
            // Find if there are specific consumer functions at risk
            const atRisk = data.at_risk_functions[nodeId];
            if (atRisk) {
                details.entities = atRisk.map(f => `${f}() [At Risk]`);
            }
        }
        
        return details;
    };
    
    const nodeDetails = getSelectedNodeDetails();

    return html`
        <div className="dashboard-container">
            <!-- Top Controls Form -->
            <header className="top-bar glass-panel">
                <div className="brand-section">
                    <${Icons.ShieldAlert} />
                    <h1 className="brand-title">Diff-Guard</h1>
                    <span className="brand-badge">v1.1</span>
                </div>
                
                <form className="controls-form" onSubmit=${handleAnalyze}>
                    <div className="input-group url">
                        <label className="input-label">GitHub Repository URL</label>
                        <input 
                            type="text" 
                            className="input-field" 
                            value=${repoUrl} 
                            onChange=${e => setRepoUrl(e.target.value)} 
                            placeholder="https://github.com/owner/repo"
                            disabled=${loading}
                            required
                        />
                    </div>
                    
                    <div className="input-group">
                        <label className="input-label">Base Ref</label>
                        <input 
                            type="text" 
                            className="input-field" 
                            value=${base} 
                            onChange=${e => setBase(e.target.value)} 
                            placeholder="main / SHA"
                            disabled=${loading}
                            required
                        />
                    </div>
                    
                    <div className="input-group">
                        <label className="input-label">Head Ref</label>
                        <input 
                            type="text" 
                            className="input-field" 
                            value=${head} 
                            onChange=${e => setHead(e.target.value)} 
                            placeholder="feature / SHA"
                            disabled=${loading}
                            required
                        />
                    </div>
                    
                    <button type="submit" className="btn-analyze" disabled=${loading}>
                        <${Icons.Play} />
                        ${loading ? 'Analyzing...' : 'Analyze'}
                    </button>
                </form>
            </header>

            <!-- Main Panel Split -->
            <main className="main-workspace">
                <!-- Left Sidebar: Score + Modified Semantic Entities -->
                <aside className="sidebar glass-panel">
                    <div className="sidebar-tabs">
                        <button 
                            className="sidebar-tab ${activeTab === 'summary' ? 'active' : ''}" 
                            onClick=${() => setActiveTab('summary')}
                        >
                            <${Icons.BarChart} />
                            <span>Summary</span>
                        </button>
                        <button 
                            className="sidebar-tab ${activeTab === 'history' ? 'active' : ''}" 
                            onClick=${() => setActiveTab('history')}
                        >
                            <${Icons.Clock} />
                            <span>History</span>
                        </button>
                    </div>
                    
                    <div className="panel-body" style=${{display: 'flex', flexDirection: 'column', gap: '20px'}}>
                        ${activeTab === 'summary' ? (
                            !data ? html`
                                <div className="empty-state">
                                    <${Icons.Terminal} />
                                    <span>Submit repo coordinates to load risk summary.</span>
                                </div>
                            ` : html`
                                <div className="risk-meter-container">
                                    <div className="risk-circle">
                                        <svg className="risk-circle-svg" width="130" height="130">
                                            <circle className="risk-circle-bg" cx="65" cy="65" r="60"/>
                                            <circle 
                                                className="risk-circle-fill" 
                                                cx="65" 
                                                cy="65" 
                                                r="60"
                                                strokeDasharray="377"
                                                strokeDashoffset=${strokeDashoffset}
                                                style=${{
                                                    stroke: riskStatus === 'low' ? 'var(--color-success)' : (riskStatus === 'medium' ? 'var(--color-warning)' : 'var(--color-danger)')
                                                }}
                                            />
                                        </svg>
                                        <div className="risk-circle-text">
                                            <span className="risk-score-value">${score}</span>
                                            <span className="risk-score-label">Score</span>
                                        </div>
                                    </div>
                                    <div className="risk-status-badge ${riskStatus}">
                                        ${data.status}
                                    </div>
                                </div>
                                
                                <!-- Changed Entities List -->
                                <div style=${{flexGrow: 1, minHeight: '0', display: 'flex', flexDirection: 'column'}}>
                                    <h3 style=${{fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '10px'}}>Modified Semantic Files</h3>
                                    <div className="file-list" style=${{overflowY: 'auto', maxHeight: '250px'}}>
                                        ${data.modified_files.length === 0 ? html`
                                            <div className="empty-state" style=${{padding: '10px'}}>No Python modifications.</div>
                                        ` : data.modified_files.map(item => html`
                                            <div 
                                                key=${item.file} 
                                                className="file-item ${selectedNode?.id === item.file ? 'selected' : ''}"
                                                onClick=${() => setSelectedNode({ id: item.file, isModified: true, isImpacted: false })}
                                            >
                                                <div className="file-item-header">
                                                    <span className="file-name" title=${item.file}>${item.file}</span>
                                                    <span className="file-badge modified">Modified</span>
                                                </div>
                                                <div className="entity-tags">
                                                    ${item.changed_entities.map(e => html`
                                                        <span key=${e.entity} className="entity-tag">${e.entity}</span>
                                                    `)}
                                                </div>
                                            </div>
                                        `)}
                                    </div>
                                </div>
                            `
                        ) : html`
                            <!-- History Tab View -->
                            <div style=${{display: 'flex', flexDirection: 'column', height: '100%'}}>
                                <div className="history-header">
                                    <h3 style=${{fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase'}}>Recent Checks</h3>
                                    ${history.length > 0 && html`
                                        <button className="btn-delete-all" onClick=${clearAllHistory}>
                                            <${Icons.Trash} />
                                            <span>Clear All</span>
                                        </button>
                                    `}
                                </div>
                                
                                <div className="history-list" style=${{overflowY: 'auto', flexGrow: 1}}>
                                    ${history.length === 0 ? html`
                                        <div className="empty-state">
                                            <${Icons.Clock} />
                                            <span style=${{marginTop: '8px'}}>No history yet. Run an analysis!</span>
                                        </div>
                                    ` : history.map(item => {
                                        const itemStatusClass = item.status.toLowerCase();
                                        return html`
                                            <div 
                                                key=${item.id} 
                                                className="history-item ${repoUrl === item.repoUrl && base === item.base && head === item.head ? 'active' : ''}"
                                                onClick=${() => loadHistoryItem(item)}
                                            >
                                                <div className="history-item-header">
                                                    <span className="history-repo" title=${item.repoName}>${item.repoName}</span>
                                                    <span className="history-score-badge ${itemStatusClass}">${item.score}%</span>
                                                </div>
                                                <div className="history-item-details">
                                                    <span className="history-refs" title="${item.base} ➔ ${item.head}">${item.base} ➔ ${item.head}</span>
                                                    <span className="history-time">${item.timestamp}</span>
                                                </div>
                                                <button className="btn-delete-item" onClick=${(e) => deleteHistoryItem(item.id, e)} title="Delete entry">
                                                    <${Icons.Trash} />
                                                </button>
                                            </div>
                                        `;
                                    })}
                                </div>
                            </div>
                        `}
                    </div>
                </aside>

                <!-- Center Panel: interactive graph -->
                <section className="graph-canvas-container glass-panel">
                    <div className="panel-header" style=${{borderRadius: '16px 16px 0 0'}}>
                        <span>Interactive Codebase Graph</span>
                        <div style=${{display: 'flex', gap: '8px', alignItems: 'center'}}>
                            <${Icons.Network} />
                        </div>
                    </div>
                    
                    <div ref=${containerRef} className="graph-canvas">
                        ${!data && html`
                            <div className="empty-state">
                                <${Icons.GitPullRequest} />
                                <h3 style=${{marginTop: '10px', color: 'var(--text-secondary)'}}>No Active Analysis</h3>
                                <p style=${{fontSize: '0.8rem', maxWidth: '300px', margin: '6px auto 0'}}>Input a public repo and trigger an analysis to render the dependency blast radius graph.</p>
                            </div>
                        `}
                    </div>

                    ${data && html`
                        <div className="graph-legend">
                            <div className="legend-item">
                                <span className="legend-color modified"></span>
                                <span>Modified File</span>
                            </div>
                            <div className="legend-item">
                                <span className="legend-color impacted"></span>
                                <span>Impacted File</span>
                            </div>
                            <div className="legend-item">
                                <span className="legend-color neutral"></span>
                                <span>No Impact</span>
                            </div>
                            <div style=${{marginLeft: 'auto', color: 'var(--text-muted)'}}>
                                <i data-lucide="help-circle" style=${{width: '12px', height: '12px', verticalAlign: 'middle', marginRight: '4px'}}></i>
                                Hover node to highlight blast radius
                            </div>
                        </div>
                    `}

                    <!-- Loading overlay -->
                    ${loading && html`
                        <div className="loading-overlay">
                            <div className="spinner"></div>
                            <span style=${{fontWeight: 500, fontSize: '0.95rem'}}>Downloading repository and computing graph dependencies...</span>
                        </div>
                    `}

                    <!-- Error display -->
                    ${error && html`
                        <div className="loading-overlay" style=${{background: 'rgba(3, 7, 18, 0.9)'}}>
                            <${Icons.XCircle} />
                            <span style=${{fontWeight: 600, color: '#f87171'}}>Analysis Failed</span>
                            <p style=${{fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: '400px', textAlign: 'center'}}>${error}</p>
                            <button className="btn-analyze" style=${{marginTop: '10px', background: 'transparent', border: '1px solid var(--border-color)'}} onClick=${() => setError(null)}>Dismiss</button>
                        </div>
                    `}

                    <!-- Floating Inspector Panel -->
                    ${nodeDetails && html`
                        <div className="floating-inspector glass-panel">
                            <div className="inspector-header">
                                <div style=${{display: 'flex', alignItems: 'center', gap: '8px'}}>
                                    <${Icons.FileCode} />
                                    <span style=${{fontWeight: 600, fontSize: '0.85rem'}}>${nodeDetails.id}</span>
                                    <span className="file-badge ${nodeDetails.status}">${nodeDetails.status}</span>
                                </div>
                                <button className="btn-close" onClick=${() => setSelectedNode(null)}>
                                    <${Icons.X} />
                                </button>
                            </div>
                            <div className="inspector-body">
                                ${nodeDetails.entities.length > 0 ? html`
                                    <div>
                                        <p style=${{color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: 600}}>Key References / At-Risk Entities:</p>
                                        <div style=${{display: 'flex', flexWrap: 'wrap', gap: '6px'}}>
                                            ${nodeDetails.entities.map(ent => html`
                                                <span key=${ent} className="entity-tag" style=${{background: 'rgba(99, 102, 241, 0.1)', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.2)'}}>${ent}</span>
                                            `)}
                                        </div>
                                    </div>
                                ` : html`
                                    <p style=${{color: 'var(--text-muted)'}}>No modified or at-risk entities detected in this file.</p>
                                `}
                            </div>
                        </div>
                    `}
                </section>

                <!-- Right Sidebar: Impacted downstream consumers -->
                <aside className="sidebar glass-panel">
                    <div className="panel-header">
                        <span>Downstream Impact</span>
                        <${Icons.Activity} />
                    </div>
                    
                    <div className="panel-body">
                        ${!data ? html`
                            <div className="empty-state">
                                <${Icons.AlertTriangle} />
                                <span>Submit repo coordinates to load downstream impacts.</span>
                            </div>
                        ` : html`
                            <!-- Impacted Files List -->
                            <div style=${{display: 'flex', flexDirection: 'column', gap: '16px'}}>
                                <div>
                                    <h3 style=${{fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px'}}>Affected Downstream Modules</h3>
                                    <p style=${{fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '10px'}}>These files import elements of changed files directly or transitively.</p>
                                    
                                    <div className="file-list" style=${{overflowY: 'auto', maxHeight: '220px'}}>
                                        ${data.all_impacted_files.length === 0 ? html`
                                            <div className="empty-state" style=${{padding: '10px'}}>🟢 No downstream modules impacted!</div>
                                        ` : data.all_impacted_files.map(file => {
                                            const atRiskFuncs = data.at_risk_functions[file] || [];
                                            return html`
                                                <div 
                                                    key=${file} 
                                                    className="file-item ${selectedNode?.id === file ? 'selected' : ''}"
                                                    onClick=${() => setSelectedNode({ id: file, isModified: false, isImpacted: true })}
                                                >
                                                    <div className="file-item-header">
                                                        <span className="file-name" title=${file}>${file}</span>
                                                        <span className="file-badge impacted">Impacted</span>
                                                    </div>
                                                    ${atRiskFuncs.length > 0 && html`
                                                        <div className="entity-tags">
                                                            ${atRiskFuncs.map(f => html`
                                                                <span key=${f} className="entity-tag" style=${{color: 'var(--color-danger)', background: 'rgba(239, 68, 68, 0.05)'}}>${f}()</span>
                                                            `)}
                                                        </div>
                                                    `}
                                                </div>
                                            `;
                                        })}
                                    </div>
                                </div>
                            </div>
                        `}
                    </div>
                </aside>
            </main>
        </div>
    `;
}
