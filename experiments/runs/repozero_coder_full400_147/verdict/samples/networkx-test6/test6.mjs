#!/usr/bin/env node

// Parse command line arguments
const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i].replace('--', '');
  const value = process.argv[i + 1];
  args[key] = parseInt(value);
}

// Create graph data structure manually
class Graph {
  constructor() {
    this.nodes = new Set();
    this.edges = new Set();
    this.adjacencyList = new Map();
  }
  
  addNode(node) {
    this.nodes.add(node);
    if (!this.adjacencyList.has(node)) {
      this.adjacencyList.set(node, []);
    }
  }
  
  addEdge(node1, node2) {
    // Add nodes if they don't exist
    this.addNode(node1);
    this.addNode(node2);
    
    // Add edge in both directions (undirected graph)
    // Store edges as pairs to properly count self-loops
    this.edges.add(`${Math.min(node1, node2)}-${Math.max(node1, node2)}`);
    this.adjacencyList.get(node1).push(node2);
    this.adjacencyList.get(node2).push(node1);
  }
  
  getNumberOfNodes() {
    return this.nodes.size;
  }
  
  getNumberOfEdges() {
    return this.edges.size;
  }
  
  getDegree(node) {
    // Count all connections including self-loops
    const neighbors = this.adjacencyList.get(node) || [];
    return neighbors.length;
  }
  
  getNeighbors(node) {
    const neighbors = this.adjacencyList.get(node);
    return neighbors ? [...new Set(neighbors)] : []; // Remove duplicates
  }
  
  getShortestPathLength(start, end) {
    // BFS to find shortest path length
    if (start === end) return 0;
    
    const visited = new Set();
    const queue = [[start, 0]];
    visited.add(start);
    
    while (queue.length > 0) {
      const [currentNode, distance] = queue.shift();
      
      for (const neighbor of this.adjacencyList.get(currentNode) || []) {
        if (neighbor === end) {
          return distance + 1;
        }
        
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push([neighbor, distance + 1]);
        }
      }
    }
    
    return -1; // No path found
  }
}

// Create and populate graph
const G = new Graph();
G.addNode(args.a);
G.addNode(args.b);
G.addNode(args.c);
G.addNode(args.d);
G.addNode(args.e);

G.addEdge(args.a, args.b);
G.addEdge(args.b, args.c);
G.addEdge(args.c, args.d);
G.addEdge(args.d, args.e);

// Output results matching Python version
console.log(G.getNumberOfNodes());
console.log(G.getNumberOfEdges());
console.log(G.getDegree(args.b));
console.log(JSON.stringify(G.getNeighbors(args.b)));
console.log(G.getShortestPathLength(args.a, args.e));