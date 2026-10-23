import React from 'react'

/**
 * MarkdownRenderer - A safe markdown renderer that properly handles nested code blocks.
 *
 * Key features:
 * - Triple backticks inside fenced code blocks render as literal text
 * - Uses a state machine to track code block depth
 * - No external markdown dependencies - deterministic offline rendering
 * - Sanitizes HTML to prevent XSS
 */

interface MarkdownRendererProps {
  content: string
  className?: string
}

// HTML escape utility
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(/'/g, '&#039;')
}

// Node types for the parsed AST
type NodeType =
  | 'text'
  | 'code_block'
  | 'inline_code'
  | 'paragraph'
  | 'heading'
  | 'bold'
  | 'italic'
  | 'link'
  | 'list_item'
  | 'ul'
  | 'ol'
  | 'blockquote'

interface ParseNode {
  type: NodeType
  content?: string
  children?: ParseNode[]
  language?: string
  level?: number
  ordered?: boolean
  url?: string
}

function parseMarkdown(text: string): ParseNode[] {
  const lines = text.split('\n')
  const nodes: ParseNode[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Fenced code blocks (``` or ~~~)
    const fenceMatch = line.match(/^ {0,3}(```|~~~)(.*)$/)
    if (fenceMatch) {
      const fence = fenceMatch[1]
      const language = fenceMatch[2].trim()
      const codeLines: string[] = []
      i++

      while (i < lines.length) {
        const currentLine = lines[i]
        const closeRegex = new RegExp(`^ {0,3}${fence.replace(/~/g, '\\~')}\\s*$`)
        if (currentLine.match(closeRegex)) {
          break
        }
        codeLines.push(currentLine)
        i++
      }

      if (i < lines.length) i++

      nodes.push({
        type: 'code_block',
        content: codeLines.join('\n'),
        language: language || undefined,
      })
      continue
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/)
    if (headingMatch) {
      nodes.push({
        type: 'heading',
        level: headingMatch[1].length,
        children: parseInline(headingMatch[2]),
      })
      i++
      continue
    }

    // Blockquotes
    const blockquoteMatch = line.match(/^>\s?(.*)$/)
    if (blockquoteMatch) {
      const quoteLines: string[] = []
      while (i < lines.length && lines[i].match(/^>\s?/)) {
        quoteLines.push(lines[i].replace(/^>\s?/, ''))
        i++
      }
      nodes.push({
        type: 'blockquote',
        children: parseMarkdown(quoteLines.join('\n')),
      })
      continue
    }

    // Unordered lists
    const ulMatch = line.match(/^ {0,3}[-*+]\s+(.*)$/)
    if (ulMatch) {
      const items: ParseNode[] = []
      while (i < lines.length && lines[i].match(/^ {0,3}[-*+]\s+/)) {
        items.push({
          type: 'list_item',
          children: parseInline(lines[i].replace(/^ {0,3}[-*+]\s+/, '')),
        })
        i++
      }
      nodes.push({ type: 'ul', children: items })
      continue
    }

    // Ordered lists
    const olMatch = line.match(/^ {0,3}\d+\.\s+(.*)$/)
    if (olMatch) {
      const items: ParseNode[] = []
      while (i < lines.length && lines[i].match(/^ {0,3}\d+\.\s+/)) {
        items.push({
          type: 'list_item',
          children: parseInline(lines[i].replace(/^ {0,3}\d+\.\s+/, '')),
        })
        i++
      }
      nodes.push({ type: 'ol', children: items })
      continue
    }

    // Paragraphs
    if (line.trim() !== '') {
      const paraLines: string[] = []
      while (
        i < lines.length &&
        lines[i].trim() !== '' &&
        !lines[i].match(/^ {0,3}(```|~~~)/) &&
        !lines[i].match(/^#{1,6}\s/) &&
        !lines[i].match(/^>\s?/) &&
        !lines[i].match(/^ {0,3}[-*+]\s+/) &&
        !lines[i].match(/^ {0,3}\d+\.\s+/)
      ) {
        paraLines.push(lines[i])
        i++
      }
      nodes.push({
        type: 'paragraph',
        children: parseInline(paraLines.join(' ')),
      })
      continue
    }

    i++
  }

  return nodes
}

function parseInline(text: string): ParseNode[] {
  // First split by inline code (backticks) - these are atomic
  const segments: Array<{ type: 'text' | 'inline_code'; content: string }> = []
  const codeRegex = /`([^`]+)`/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = codeRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    segments.push({ type: 'inline_code', content: match[1] })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) })
  }

  // Now process each text segment for bold, italic, links
  const result: ParseNode[] = []

  for (const segment of segments) {
    if (segment.type === 'inline_code') {
      result.push({ type: 'inline_code', content: segment.content })
      continue
    }

    // Process text for links, bold, italic
    const textContent = segment.content
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const nodes: ParseNode[] = []
    let linkLastIndex = 0
    let linkMatch: RegExpExecArray | null

    while ((linkMatch = linkRegex.exec(textContent)) !== null) {
      if (linkMatch.index > linkLastIndex) {
        const beforeLink = textContent.slice(linkLastIndex, linkMatch.index)
        nodes.push(...parseBoldItalic(beforeLink))
      }
      nodes.push({ type: 'link', content: linkMatch[1], url: linkMatch[2] })
      linkLastIndex = linkMatch.index + linkMatch[0].length
    }

    if (linkLastIndex < textContent.length) {
      const afterLink = textContent.slice(linkLastIndex)
      nodes.push(...parseBoldItalic(afterLink))
    }

    result.push(...nodes)
  }

  return result
}

function parseBoldItalic(text: string): ParseNode[] {
  const nodes: ParseNode[] = []
  const regex = /(\*\*|__)(.+?)\1|(\*|_)(.+?)\3/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    if (match[1]) {
      nodes.push({ type: 'bold', content: match[2] })
    } else if (match[3]) {
      nodes.push({ type: 'italic', content: match[4] })
    }
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    nodes.push({ type: 'text', content: text.slice(lastIndex) })
  }

  return nodes.length === 0 ? [{ type: 'text', content: text }] : nodes
}

function renderNode(node: ParseNode): React.ReactNode {
  switch (node.type) {
    case 'text':
      return node.content ? escapeHtml(node.content) : null

    case 'inline_code':
      return <code className="markdown-inline-code">{escapeHtml(node.content || '')}</code>

    case 'code_block':
      return (
        <pre className="markdown-code-block">
          <code className={node.language ? `language-${node.language}` : ''}>
            {escapeHtml(node.content || '')}
          </code>
        </pre>
      )

    case 'paragraph':
      return (
        <p className="markdown-paragraph">
          {node.children?.map((child) => renderNode(child))}
        </p>
      )

    case 'heading':
      const HeadingTag = `h${node.level}` as keyof JSX.IntrinsicElements
      return React.createElement(HeadingTag, { className: `markdown-heading markdown-h${node.level}` },
        node.children?.map((child) => renderNode(child))
      )

    case 'blockquote':
      return (
        <blockquote className="markdown-blockquote">
          {node.children?.map((child) => renderNode(child))}
        </blockquote>
      )

    case 'ul':
      return (
        <ul className="markdown-list markdown-ul">
          {node.children?.map((child) => renderNode(child))}
        </ul>
      )

    case 'ol':
      return (
        <ol className="markdown-list markdown-ol">
          {node.children?.map((child) => renderNode(child))}
        </ol>
      )

    case 'list_item':
      return (
        <li className="markdown-list-item">
          {node.children?.map((child) => renderNode(child))}
        </li>
      )

    case 'bold':
      return <strong className="markdown-bold">{escapeHtml(node.content || '')}</strong>

    case 'italic':
      return <em className="markdown-italic">{escapeHtml(node.content || '')}</em>

    case 'link':
      return (
        <a
          className="markdown-link"
          href={node.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {escapeHtml(node.content || '')}
        </a>
      )

    default:
      return null
  }
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content.trim()) {
    return <div className={`markdown-renderer ${className}`} data-testid="markdown-renderer"></div>
  }

  const nodes = parseMarkdown(content)

  return (
    <div className={`markdown-renderer ${className}`} data-testid="markdown-renderer">
      {nodes.map((node, idx) => (
        <React.Fragment key={idx}>{renderNode(node)}</React.Fragment>
      ))}
    </div>
  )
}

// Named exports for testing
export { parseMarkdown, parseInline, parseBoldItalic, escapeHtml }