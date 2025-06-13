'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from '@/lib/api';

interface ProgressDashboardProps {
  onBack: () => void;
}

interface TopicNode {
  id: number;
  name: string;
  parent_id: number | null;
  mastery_level: string;
  accuracy: number;
  questions_answered: number;
  is_unlocked: boolean;
  unlocked_at?: string;
  children?: TopicNode[];
  x?: number;
  y?: number;
  expanded?: boolean;
}

interface UserProgress {
  total_topics_unlocked: number;
  overall_accuracy: number;
  total_questions_answered: number;
  current_streak: number;
  learning_velocity: number;
  topics: TopicNode[];
}

export function ProgressDashboard({ onBack }: ProgressDashboardProps) {
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<TopicNode | null>(null);
  const [viewMode, setViewMode] = useState<'tree' | 'stats'>('tree');
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchProgress();
    
    // Update dimensions on resize
    const handleResize = () => {
      if (svgRef.current) {
        const rect = svgRef.current.parentElement?.getBoundingClientRect();
        if (rect) {
          setDimensions({ width: rect.width, height: rect.height });
        }
      }
    };
    
    handleResize();
    window.addEventListener('resize', handleResize);
    
    // Set up periodic refresh to catch new topics
    const refreshInterval = setInterval(fetchProgress, 30000); // Refresh every 30 seconds
    
    return () => {
      window.removeEventListener('resize', handleResize);
      clearInterval(refreshInterval);
    };
  }, []);

  const fetchProgress = async () => {
    try {
      const data = await apiService.getUserProgressData(1);
      
      // Build hierarchical tree from flat data
      const topicMap = new Map<number, TopicNode>();
      const roots: TopicNode[] = [];
      
      // First pass: create all nodes
      data.topics.forEach((topic: TopicNode) => {
        topicMap.set(topic.id, { ...topic, children: [], expanded: false });
      });
      
      // Second pass: build tree structure
      data.topics.forEach((topic: TopicNode) => {
        const node = topicMap.get(topic.id)!;
        if (topic.parent_id === null) {
          roots.push(node);
        } else {
          const parent = topicMap.get(topic.parent_id);
          if (parent) {
            parent.children!.push(node);
          }
        }
      });
      
      // Calculate positions for tree layout
      if (roots.length > 0) {
        calculateTreeLayout(roots[0], dimensions.width / 2, 100, dimensions.width / 4);
        
        // Initialize expanded nodes - expand root and its children by default
        const initialExpanded = new Set<number>();
        initialExpanded.add(roots[0].id);
        roots[0].children?.forEach(child => {
          initialExpanded.add(child.id);
        });
        setExpandedNodes(initialExpanded);
      }
      
      setProgress({
        ...data,
        topics: roots
      });
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch progress:', error);
      setLoading(false);
    }
  };

  const calculateTreeLayout = (node: TopicNode, x: number, y: number, spread: number, level: number = 0) => {
    node.x = x;
    node.y = y;
    
    // Only layout children if node is expanded
    if (node.children && node.children.length > 0 && expandedNodes.has(node.id)) {
      // Filter only visible children
      const visibleChildren = node.children;
      
      if (visibleChildren.length > 0) {
        // Adjust spread based on number of children to prevent overlap
        const childSpread = Math.max(80, spread / Math.max(1.2, visibleChildren.length * 0.3));
        const totalWidth = childSpread * (visibleChildren.length - 1);
        const startX = x - totalWidth / 2;
        
        visibleChildren.forEach((child, index) => {
          const childX = startX + (index * childSpread);
          calculateTreeLayout(child, childX, y + 120, childSpread, level + 1);
        });
      }
    }
  };

  const handleNodeClick = (node: TopicNode) => {
    setSelectedNode(node);
  };

  const toggleNodeExpansion = (nodeId: number) => {
    setExpandedNodes(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(nodeId)) {
        newExpanded.delete(nodeId);
      } else {
        newExpanded.add(nodeId);
      }
      return newExpanded;
    });
    
    // Recalculate layout after expansion change
    if (progress?.topics && progress.topics.length > 0) {
      calculateTreeLayout(progress.topics[0], dimensions.width / 2, 100, dimensions.width / 4);
      setProgress({ ...progress });
    }
  };

  const handleStartLearning = async (node: TopicNode) => {
    try {
      // First, navigate to the topic to ensure it's unlocked and set interest
      await apiService.navigateToTopic(node.id, 1);
      
      // Then navigate back to adaptive learning - the parent component should handle this
      // For now, we'll just show a success message
      alert(`Ready to learn ${node.name}! You can now go back to the main learning page.`);
      
    } catch (error) {
      console.error('Failed to start learning topic:', error);
      alert('Unable to start learning this topic. Please try again.');
    }
  };

  const getNodeColor = (node: TopicNode) => {
    if (!node.is_unlocked) return '#94a3b8'; // gray for locked
    if (node.accuracy >= 0.8) return '#10b981'; // green for mastered
    if (node.accuracy >= 0.6) return '#3b82f6'; // blue for learning
    if (node.accuracy >= 0.4) return '#f59e0b'; // yellow for struggling
    return '#ef4444'; // red for needs work
  };

  const isUserGeneratedTopic = (node: TopicNode) => {
    // Check if this is a recently created topic
    // Topics that are unlocked but have no progress might be user-generated
    // Also check if they were unlocked very recently (within last hour)
    const isRecent = node.unlocked_at && 
      new Date(node.unlocked_at).getTime() > Date.now() - (60 * 60 * 1000); // Last hour
    
    return node.questions_answered === 0 && 
           node.is_unlocked && 
           isRecent &&
           node.mastery_level === 'novice';
  };

  const renderNode = (node: TopicNode) => {
    const color = getNodeColor(node);
    const isSelected = selectedNode?.id === node.id;
    const isUserGenerated = isUserGeneratedTopic(node);
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    
    return (
      <g key={node.id}>
        {/* Draw connections to children only if expanded */}
        {isExpanded && node.children?.map(child => (
          <line
            key={`${node.id}-${child.id}`}
            x1={node.x}
            y1={node.y}
            x2={child.x}
            y2={child.y}
            stroke="#e5e7eb"
            strokeWidth="2"
          />
        ))}
        
        {/* Node circle */}
        <circle
          cx={node.x}
          cy={node.y}
          r={isSelected ? 25 : 20}
          fill={color}
          stroke={isSelected ? '#1f2937' : isUserGenerated ? '#f59e0b' : 'white'}
          strokeWidth={isSelected ? 3 : isUserGenerated ? 2 : 1.5}
          strokeDasharray={isUserGenerated ? '5,5' : 'none'}
          style={{ cursor: 'pointer', transition: 'all 0.2s' }}
          onClick={() => handleNodeClick(node)}
        />
        
        {/* User-generated topic indicator */}
        {isUserGenerated && (
          <circle
            cx={node.x! + 15}
            cy={node.y! - 15}
            r="6"
            fill="#f59e0b"
            stroke="white"
            strokeWidth="1.5"
          />
        )}
        
        {isUserGenerated && (
          <text
            x={node.x! + 15}
            y={node.y! - 12}
            textAnchor="middle"
            className="text-xs font-bold fill-white"
            style={{ pointerEvents: 'none', fontSize: '10px' }}
          >
            ✨
          </text>
        )}
        
        {/* Node text */}
        <text
          x={node.x}
          y={node.y! + 40}
          textAnchor="middle"
          className="text-xs font-medium fill-gray-900 dark:fill-gray-100"
          style={{ pointerEvents: 'none' }}
        >
          {node.name.length > 15 ? node.name.substring(0, 15) + '...' : node.name}
        </text>
        
        {/* Progress indicator */}
        {node.is_unlocked && node.questions_answered > 0 && (
          <text
            x={node.x}
            y={node.y! + 3}
            textAnchor="middle"
            className="text-xs font-bold fill-white"
            style={{ pointerEvents: 'none', fontSize: '10px' }}
          >
            {Math.round(node.accuracy * 100)}%
          </text>
        )}
        
        {/* Lock icon for locked nodes */}
        {!node.is_unlocked && (
          <text
            x={node.x}
            y={node.y! + 5}
            textAnchor="middle"
            style={{ pointerEvents: 'none', fontSize: '14px' }}
          >
            🔒
          </text>
        )}
        
        {/* Expand/Collapse indicator */}
        {hasChildren && (
          <g
            onClick={(e) => {
              e.stopPropagation();
              toggleNodeExpansion(node.id);
            }}
            style={{ cursor: 'pointer' }}
          >
            <circle
              cx={node.x}
              cy={node.y! + 28}
              r="8"
              fill="white"
              stroke="#6b7280"
              strokeWidth="1.5"
            />
            <text
              x={node.x}
              y={node.y! + 32}
              textAnchor="middle"
              className="text-xs font-bold fill-gray-700 dark:fill-gray-600"
              style={{ pointerEvents: 'none', fontSize: '10px' }}
            >
              {isExpanded ? '−' : '+'}
            </text>
          </g>
        )}
        
        {/* Render children only if expanded */}
        {isExpanded && node.children?.map(child => renderNode(child))}
      </g>
    );
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setTransform({
        ...transform,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    // Reduce zoom sensitivity - smaller delta values
    const delta = e.deltaY > 0 ? 0.95 : 1.05;
    setTransform({
      ...transform,
      scale: Math.max(0.3, Math.min(3, transform.scale * delta))
    });
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Learning Progress & Ontology Explorer
            </h2>
            <div className="flex items-center gap-4">
              <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('tree')}
                  className={`px-4 py-2 rounded-md transition-colors ${
                    viewMode === 'tree'
                      ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  🌳 Tree View
                </button>
                <button
                  onClick={() => setViewMode('stats')}
                  className={`px-4 py-2 rounded-md transition-colors ${
                    viewMode === 'stats'
                      ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  📊 Statistics
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchProgress}
                  disabled={loading}
                  className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                >
                  {loading ? '🔄' : '🔄'} Refresh
                </button>
                <button
                  onClick={onBack}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
                >
                  Back to Learning
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex">
          {/* Left Panel - Tree Visualization */}
          <div className="flex-1 p-6">
            {viewMode === 'tree' ? (
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4" style={{ height: '600px' }}>
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    🌳 Your Knowledge Tree
                  </h3>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          // Expand all nodes
                          const allNodeIds = new Set<number>();
                          const collectNodeIds = (node: TopicNode) => {
                            allNodeIds.add(node.id);
                            node.children?.forEach(collectNodeIds);
                          };
                          progress?.topics.forEach(collectNodeIds);
                          setExpandedNodes(allNodeIds);
                          
                          // Recalculate layout
                          if (progress?.topics && progress.topics.length > 0) {
                            calculateTreeLayout(progress.topics[0], dimensions.width / 2, 100, dimensions.width / 4);
                            setProgress({ ...progress });
                          }
                        }}
                        className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                      >
                        Expand All
                      </button>
                      <button
                        onClick={() => {
                          // Collapse all except root and its children
                          const newExpanded = new Set<number>();
                          if (progress?.topics && progress.topics.length > 0) {
                            newExpanded.add(progress.topics[0].id);
                            progress.topics[0].children?.forEach(child => {
                              newExpanded.add(child.id);
                            });
                          }
                          setExpandedNodes(newExpanded);
                          
                          // Recalculate layout
                          if (progress?.topics && progress.topics.length > 0) {
                            calculateTreeLayout(progress.topics[0], dimensions.width / 2, 100, dimensions.width / 4);
                            setProgress({ ...progress });
                          }
                        }}
                        className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                      >
                        Collapse All
                      </button>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <span>🖱️ Drag to pan</span>
                      <span>🔍 Scroll to zoom</span>
                    </div>
                  </div>
                </div>
                
                <div className="relative overflow-hidden bg-gray-50 dark:bg-gray-700 rounded-lg" style={{ height: '500px' }}>
                  <svg
                    ref={svgRef}
                    width="100%"
                    height="100%"
                    style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                    onWheel={handleWheel}
                  >
                    <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
                      {progress?.topics.map(topic => renderNode(topic))}
                    </g>
                  </svg>
                </div>

                {/* Legend */}
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full bg-green-500"></div>
                      <span className="text-gray-600 dark:text-gray-400">Mastered (80%+)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full bg-blue-500"></div>
                      <span className="text-gray-600 dark:text-gray-400">Learning (60%+)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
                      <span className="text-gray-600 dark:text-gray-400">Struggling (40%+)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full bg-gray-400"></div>
                      <span className="text-gray-600 dark:text-gray-400">Locked</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <div className="w-4 h-4 rounded-full bg-blue-500 border-2 border-yellow-500" style={{borderStyle: 'dashed'}}></div>
                        <div className="absolute -top-1 -right-1 text-xs">✨</div>
                      </div>
                      <span className="text-gray-600 dark:text-gray-400">Your Request</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                    <span>💡 Click + to expand branches</span>
                    <span>👆 Click node to see details</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Overall Stats */}
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    📊 Overall Statistics
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-600 dark:text-gray-400">Topics Unlocked</span>
                        <span className="font-semibold">{progress?.total_topics_unlocked || 0}</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, (progress?.total_topics_unlocked || 0) * 5)}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-600 dark:text-gray-400">Overall Accuracy</span>
                        <span className="font-semibold">
                          {Math.round((progress?.overall_accuracy || 0) * 100)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-green-600 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${(progress?.overall_accuracy || 0) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="pt-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Questions Answered</span>
                        <span className="font-semibold">{progress?.total_questions_answered || 0}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Learning Velocity */}
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    🚀 Learning Progress
                  </h3>
                  <div className="space-y-4">
                    <div className="text-center py-4">
                      <div className="text-4xl font-bold text-blue-600 dark:text-blue-400">
                        {progress?.current_streak || 0}
                      </div>
                      <div className="text-gray-600 dark:text-gray-400">Day Streak</div>
                    </div>
                    
                    <div className="text-center">
                      <div className="text-2xl font-semibold text-green-600 dark:text-green-400">
                        {((progress?.learning_velocity || 0) * 100).toFixed(1)}%
                      </div>
                      <div className="text-gray-600 dark:text-gray-400">Learning Velocity</div>
                    </div>
                  </div>
                </div>

                {/* Topic Mastery Distribution */}
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 md:col-span-2">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    🎯 Topic Mastery Distribution
                  </h3>
                  <div className="space-y-3">
                    {progress?.topics[0]?.children?.map(topic => (
                      <div key={topic.id}>
                        <div className="flex justify-between mb-1">
                          <span className="text-gray-700 dark:text-gray-300">{topic.name}</span>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {topic.is_unlocked ? `${Math.round(topic.accuracy * 100)}%` : '🔒 Locked'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-500 ${
                              topic.is_unlocked ? getNodeColor(topic) : 'bg-gray-400'
                            }`}
                            style={{ 
                              width: topic.is_unlocked ? `${topic.accuracy * 100}%` : '0%',
                              backgroundColor: topic.is_unlocked ? getNodeColor(topic) : undefined
                            }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - Node Details */}
          {selectedNode && viewMode === 'tree' && (
            <div className="w-80 border-l border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                📋 Topic Details
              </h3>
              
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">{selectedNode.name}</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {selectedNode.is_unlocked ? 'Unlocked' : 'Locked - Complete prerequisites'}
                  </p>
                </div>
                
                {selectedNode.is_unlocked && (
                  <>
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                      <div className="flex justify-between mb-2">
                        <span className="text-gray-600 dark:text-gray-400">Accuracy</span>
                        <span className="font-semibold">
                          {Math.round(selectedNode.accuracy * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between mb-2">
                        <span className="text-gray-600 dark:text-gray-400">Questions</span>
                        <span className="font-semibold">{selectedNode.questions_answered}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Mastery</span>
                        <span className="font-semibold capitalize">{selectedNode.mastery_level}</span>
                      </div>
                    </div>
                    
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                      <div className="text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Status: </span>
                        <span className={`font-medium ${
                          selectedNode.accuracy >= 0.8 ? 'text-green-600' :
                          selectedNode.accuracy >= 0.6 ? 'text-blue-600' :
                          selectedNode.accuracy >= 0.4 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {selectedNode.accuracy >= 0.8 ? 'Mastered' :
                           selectedNode.accuracy >= 0.6 ? 'Learning' :
                           selectedNode.accuracy >= 0.4 ? 'Needs Practice' :
                           'Just Started'}
                        </span>
                      </div>
                    </div>
                    
                    {/* Start Learning Button */}
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                      <button
                        onClick={() => handleStartLearning(selectedNode)}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                      >
                        🚀 Start Learning
                      </button>
                    </div>
                  </>
                )}
                
                {!selectedNode.is_unlocked && (
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                    <p className="text-sm text-yellow-800 dark:text-yellow-200">
                      Complete prerequisite topics with 60% accuracy and answer at least 3 questions to unlock.
                    </p>
                  </div>
                )}
                
                {selectedNode.children && selectedNode.children.length > 0 && (
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                    <h5 className="font-medium text-gray-900 dark:text-white mb-2">
                      Child Topics ({selectedNode.children.length})
                    </h5>
                    <ul className="space-y-1">
                      {selectedNode.children.map(child => (
                        <li key={child.id} className="text-sm text-gray-600 dark:text-gray-400">
                          {child.is_unlocked ? '✅' : '🔒'} {child.name}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}