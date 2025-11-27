/**
 * Central specs helper module for consistent spec handling across the UI.
 * 
 * This module provides:
 * - Tree building utilities for hierarchical specs
 * - Shared types for spec nodes
 * - Helper functions for spec display and formatting
 */

import type { LotSpec, SpecTemplate } from './api';

// =============================================================================
// Shared Types
// =============================================================================

/**
 * A spec node with children for tree display.
 * Extends LotSpec with tree-related properties.
 */
export interface SpecNode extends LotSpec {
  children: SpecNode[];
  depth: number;
}

/**
 * A template node with children for tree display.
 * Extends SpecTemplate with tree-related properties.
 */
export interface TemplateNode extends SpecTemplate {
  children: TemplateNode[];
  depth: number;
}

// =============================================================================
// Tree Building Functions
// =============================================================================

/**
 * Build a hierarchical tree from a flat list of specs.
 * @param specs Flat array of specs with parent_id references
 * @returns Array of root SpecNodes with nested children
 */
export function buildSpecTree(specs: LotSpec[]): SpecNode[] {
  const map = new Map<number, SpecNode>();
  const roots: SpecNode[] = [];

  // First pass: create nodes with initial depth 0
  for (const spec of specs) {
    map.set(spec.id, { ...spec, children: [], depth: 0 });
  }

  // Second pass: build tree structure
  for (const spec of specs) {
    const node = map.get(spec.id)!;
    if (spec.parent_id && map.has(spec.parent_id)) {
      const parent = map.get(spec.parent_id)!;
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  // Third pass: calculate correct depths recursively
  function setDepths(node: SpecNode, depth: number) {
    node.depth = depth;
    for (const child of node.children) {
      setDepths(child, depth + 1);
    }
  }
  for (const root of roots) {
    setDepths(root, 0);
  }

  return roots;
}

/**
 * Build a hierarchical tree from a flat list of templates.
 * @param templates Flat array of templates with parent_id references
 * @returns Array of root TemplateNodes with nested children
 */
export function buildTemplateTree(templates: SpecTemplate[]): TemplateNode[] {
  const map = new Map<number, TemplateNode>();
  const roots: TemplateNode[] = [];

  // First pass: create nodes with initial depth 0
  for (const template of templates) {
    map.set(template.id, { ...template, children: [], depth: 0 });
  }

  // Second pass: build tree structure
  for (const template of templates) {
    const node = map.get(template.id)!;
    if (template.parent_id && map.has(template.parent_id)) {
      const parent = map.get(template.parent_id)!;
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  // Third pass: calculate correct depths recursively
  function setDepths(node: TemplateNode, depth: number) {
    node.depth = depth;
    for (const child of node.children) {
      setDepths(child, depth + 1);
    }
  }
  for (const root of roots) {
    setDepths(root, 0);
  }

  return roots;
}

// =============================================================================
// Flattening Functions (for table/list display)
// =============================================================================

/**
 * Flatten a spec tree to a list with depth information preserved.
 * Useful for rendering in tables where you need flat rows but with indentation.
 * @param tree Array of root SpecNodes
 * @returns Flat array with depth property for indentation
 */
export function flattenSpecTree(tree: SpecNode[]): SpecNode[] {
  const result: SpecNode[] = [];

  function traverse(nodes: SpecNode[]) {
    for (const node of nodes) {
      result.push(node);
      traverse(node.children);
    }
  }

  traverse(tree);
  return result;
}

/**
 * Flatten a template tree to a list with depth information preserved.
 * @param tree Array of root TemplateNodes
 * @returns Flat array with depth property for indentation
 */
export function flattenTemplateTree(tree: TemplateNode[]): TemplateNode[] {
  const result: TemplateNode[] = [];

  function traverse(nodes: TemplateNode[]) {
    for (const node of nodes) {
      result.push(node);
      traverse(node.children);
    }
  }

  traverse(tree);
  return result;
}

// =============================================================================
// Display Helpers
// =============================================================================

/**
 * Depth-based colors for visual indentation.
 * Colors cycle after depth 4.
 */
export const DEPTH_COLORS = [
  '#6366f1', // indigo - depth 0
  '#22c55e', // green - depth 1
  '#f59e0b', // amber - depth 2
  '#ef4444', // red - depth 3
  '#8b5cf6', // violet - depth 4
  '#06b6d4', // cyan - depth 5
] as const;

/**
 * Get the border color for a given depth level.
 * @param depth The depth level (0-based)
 * @returns CSS color string
 */
export function getDepthColor(depth: number): string {
  return DEPTH_COLORS[depth % DEPTH_COLORS.length];
}

/**
 * Get CSS styles for depth-based indentation.
 * @param depth The depth level (0-based)
 * @returns CSS style object for React
 */
export function getDepthStyles(depth: number): React.CSSProperties {
  if (depth === 0) {
    return {};
  }
  return {
    paddingLeft: `${depth * 24}px`,
    borderLeft: `3px solid ${getDepthColor(depth)}`,
  };
}

/**
 * Format a spec/template for display.
 * Shows key: value or just key if no value.
 * @param item Spec or template with key/title and optional value
 * @returns Formatted string
 */
export function formatSpecDisplay(item: { key?: string; title?: string; value?: string | null }): string {
  const label = item.key || item.title || '';
  if (item.value) {
    return `${label}: ${item.value}`;
  }
  return label;
}

/**
 * Format price for display.
 * @param priceEur Price in EUR or null
 * @returns Formatted price string or empty string
 */
export function formatPrice(priceEur: number | null | undefined): string {
  if (priceEur == null) {
    return '';
  }
  return new Intl.NumberFormat('nl-NL', {
    style: 'currency',
    currency: 'EUR',
  }).format(priceEur);
}

/**
 * Format date for display.
 * @param dateStr ISO date string or null
 * @returns Formatted date string or empty string
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) {
    return '';
  }
  try {
    return new Date(dateStr).toLocaleDateString('nl-NL');
  } catch {
    return dateStr;
  }
}

// =============================================================================
// Lookup Helpers
// =============================================================================

/**
 * Find a spec by ID in a flat list.
 * @param specs Flat array of specs
 * @param id ID to find
 * @returns Found spec or undefined
 */
export function findSpecById(specs: LotSpec[], id: number): LotSpec | undefined {
  return specs.find(s => s.id === id);
}

/**
 * Find a template by ID in a flat list.
 * @param templates Flat array of templates
 * @param id ID to find
 * @returns Found template or undefined
 */
export function findTemplateById(templates: SpecTemplate[], id: number): SpecTemplate | undefined {
  return templates.find(t => t.id === id);
}

/**
 * Get all root-level specs (no parent).
 * @param specs Flat array of specs
 * @returns Array of root specs
 */
export function getRootSpecs(specs: LotSpec[]): LotSpec[] {
  return specs.filter(s => s.parent_id === null);
}

/**
 * Get all root-level templates (no parent).
 * @param templates Flat array of templates
 * @returns Array of root templates
 */
export function getRootTemplates(templates: SpecTemplate[]): SpecTemplate[] {
  return templates.filter(t => t.parent_id === null);
}

/**
 * Get child specs of a parent.
 * @param specs Flat array of specs
 * @param parentId Parent spec ID
 * @returns Array of child specs
 */
export function getChildSpecs(specs: LotSpec[], parentId: number): LotSpec[] {
  return specs.filter(s => s.parent_id === parentId);
}

/**
 * Get child templates of a parent.
 * @param templates Flat array of templates
 * @param parentId Parent template ID
 * @returns Array of child templates
 */
export function getChildTemplates(templates: SpecTemplate[], parentId: number): SpecTemplate[] {
  return templates.filter(t => t.parent_id === parentId);
}

/**
 * Check if a spec has children.
 * @param specs Flat array of specs
 * @param specId Spec ID to check
 * @returns True if spec has children
 */
export function hasChildren(specs: LotSpec[], specId: number): boolean {
  return specs.some(s => s.parent_id === specId);
}

/**
 * Get the full path of a spec (ancestor titles).
 * @param specs Flat array of specs
 * @param specId Spec ID
 * @returns Array of keys from root to spec
 */
export function getSpecPath(specs: LotSpec[], specId: number): string[] {
  const path: string[] = [];
  let current = findSpecById(specs, specId);
  
  while (current) {
    path.unshift(current.key);
    current = current.parent_id ? findSpecById(specs, current.parent_id) : undefined;
  }
  
  return path;
}

/**
 * Get the full path of a template (ancestor titles).
 * @param templates Flat array of templates
 * @param templateId Template ID
 * @returns Array of titles from root to template
 */
export function getTemplatePath(templates: SpecTemplate[], templateId: number): string[] {
  const path: string[] = [];
  let current = findTemplateById(templates, templateId);
  
  while (current) {
    path.unshift(current.title);
    current = current.parent_id ? findTemplateById(templates, current.parent_id) : undefined;
  }
  
  return path;
}
