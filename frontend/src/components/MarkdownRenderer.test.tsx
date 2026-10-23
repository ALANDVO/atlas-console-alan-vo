import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownRenderer, parseMarkdown, parseInline, escapeHtml } from './MarkdownRenderer'

describe('MarkdownRenderer', () => {
  describe('escapeHtml', () => {
    it('escapes HTML special characters', () => {
      expect(escapeHtml('<script>alert(1)</script>')).toBe('<script>alert(1)</script>')
      expect(escapeHtml('"quoted" & <tag>')).toBe('"quoted" & <tag>')
      expect(escapeHtml("O'Reilly")).toBe('O&#039;Reilly')
    })

    it('leaves plain text unchanged', () => {
      expect(escapeHtml('plain text')).toBe('plain text')
      expect(escapeHtml('')).toBe('')
    })
  })

  describe('parseMarkdown - code blocks', () => {
    it('parses simple fenced code block', () => {
      const md = '```js\nconsole.log("hello")\n```'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(1)
      expect(nodes[0].type).toBe('code_block')
      expect(nodes[0].language).toBe('js')
      expect(nodes[0].content).toBe('console.log("hello")')
    })

    it('parses code block without language', () => {
      const md = '```\nplain text\n```'
      const nodes = parseMarkdown(md)
      expect(nodes[0].type).toBe('code_block')
      expect(nodes[0].language).toBeUndefined()
      expect(nodes[0].content).toBe('plain text')
    })

    it('handles nested triple backticks inside code block as literal text', () => {
      const md = '```\nTo run a command, use ```nmap -sV 10.0.1.50```\n```'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(1)
      expect(nodes[0].type).toBe('code_block')
      expect(nodes[0].content).toBe('To run a command, use ```nmap -sV 10.0.1.50```')
    })

    it('handles multiple code blocks in sequence', () => {
      const md = '```js\nfirst\n```\n\n```python\nsecond\n```'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(2)
      expect(nodes[0].language).toBe('js')
      expect(nodes[1].language).toBe('python')
    })

    it('handles tilde fences', () => {
      const md = '~~~\ntilde fence\n~~~'
      const nodes = parseMarkdown(md)
      expect(nodes[0].type).toBe('code_block')
      expect(nodes[0].content).toBe('tilde fence')
    })

    it('nested tilde fences inside backtick block are literal', () => {
      const md = '```\n~~~nested~~~\n```'
      const nodes = parseMarkdown(md)
      expect(nodes[0].content).toBe('~~~nested~~~')
    })
  })

  describe('parseMarkdown - headings', () => {
    it('parses headings 1-6', () => {
      const md = '# H1\n## H2\n### H3'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(3)
      expect(nodes[0].type).toBe('heading')
      expect(nodes[0].level).toBe(1)
      expect(nodes[1].level).toBe(2)
      expect(nodes[2].level).toBe(3)
    })

    it('heading with inline formatting', () => {
      const md = '# **Bold** heading'
      const nodes = parseMarkdown(md)
      expect(nodes[0].children).toBeDefined()
      expect(nodes[0].children!.some(c => c.type === 'bold')).toBe(true)
    })
  })

  describe('parseMarkdown - paragraphs', () => {
    it('parses simple paragraph', () => {
      const md = 'This is a paragraph.'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(1)
      expect(nodes[0].type).toBe('paragraph')
    })

    it('multi-line paragraph joins with spaces', () => {
      const md = 'Line one\nLine two\nLine three'
      const nodes = parseMarkdown(md)
      expect(nodes[0].type).toBe('paragraph')
      // Content should be joined
      expect(nodes[0].children).toBeDefined()
    })

    it('empty lines separate paragraphs', () => {
      const md = 'First para\n\nSecond para'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(2)
      expect(nodes[0].type).toBe('paragraph')
      expect(nodes[1].type).toBe('paragraph')
    })
  })

  describe('parseMarkdown - lists', () => {
    it('parses unordered list', () => {
      const md = '- Item 1\n- Item 2'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(1)
      expect(nodes[0].type).toBe('ul')
      expect(nodes[0].children).toHaveLength(2)
    })

    it('parses ordered list', () => {
      const md = '1. First\n2. Second'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(1)
      expect(nodes[0].type).toBe('ol')
      expect(nodes[0].children).toHaveLength(2)
    })

    it('list items with inline code', () => {
      const md = '- Use `npm install`'
      const nodes = parseMarkdown(md)
      const item = nodes[0].children![0]
      expect(item.type).toBe('list_item')
      expect(item.children!.some(c => c.type === 'inline_code')).toBe(true)
    })
  })

  describe('parseMarkdown - blockquotes', () => {
    it('parses blockquote', () => {
      const md = '> Quote line 1\n> Quote line 2'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(1)
      expect(nodes[0].type).toBe('blockquote')
      expect(nodes[0].children).toHaveLength(1) // paragraph
    })

    it('nested blockquote content', () => {
      const md = '> **Bold** quote'
      const nodes = parseMarkdown(md)
      const para = nodes[0].children![0]
      expect(para.type).toBe('paragraph')
      expect(para.children!.some(c => c.type === 'bold')).toBe(true)
    })
  })

  describe('parseMarkdown - mixed content', () => {
    it('parses complex markdown with code blocks and text', () => {
      const md = 'Intro text\n\n```js\ncode()\n```\n\nOutro text'
      const nodes = parseMarkdown(md)
      expect(nodes).toHaveLength(3)
      expect(nodes[0].type).toBe('paragraph')
      expect(nodes[1].type).toBe('code_block')
      expect(nodes[2].type).toBe('paragraph')
    })

    it('handles the reproduction case from issue #361', () => {
      const md = `To run a network scan, the command is \`\`\`nmap -sV 10.0.1.50\`\`\` then check the results.

The markdown syntax for a code block is: open with \`\`\`bash, write your code, then close with \`\`\`.

For example, to display JSON:

\`\`\`json
{"flowId": 85, "action": "finish"}
\`\`\`

And here is the server response:

\`\`\`json
{"errors": [{"message": "flow not found"}]}
\`\`\`

The command \`\`\`psql -U pentagi -d pentagi -c "SELECT * FROM flows"\`\`\` checks the database state. If the result shows \`\`\`waiting\`\`\` for a flow that should be \`\`\`finished\`\`\`, it means the provider was renamed.

To fix it, run \`\`\`UPDATE flows SET model_provider_name = 'OllamaC GLM' WHERE model_provider_name = 'Ollama cloud GLM';\`\`\` then restart with \`\`\`systemctl restart pentagi\`\`\`.`

      const nodes = parseMarkdown(md)

      // Should have 2 actual fenced code blocks (the JSON ones)
      const codeBlocks = nodes.filter(n => n.type === 'code_block')
      expect(codeBlocks.length).toBe(2)

      // Verify the JSON code blocks are parsed correctly
      expect(codeBlocks[0].language).toBe('json')
      expect(codeBlocks[0].content).toContain('flowId')
      expect(codeBlocks[1].language).toBe('json')
      expect(codeBlocks[1].content).toContain('errors')

      // Verify inline triple backticks are parsed as inline_code in paragraphs
      const paragraphs = nodes.filter(n => n.type === 'paragraph')
      const allInlineCode = paragraphs.flatMap(p => 
        (p.children || []).filter(c => c.type === 'inline_code')
      )
      expect(allInlineCode.length).toBeGreaterThan(0)
      // Check that nested backticks appear in inline code
      const inlineCodeContents = allInlineCode.map(c => c.content || '')
      expect(inlineCodeContents.some(c => c.includes('nmap'))).toBe(true)
      expect(inlineCodeContents.some(c => c.includes('bash'))).toBe(true)
      expect(inlineCodeContents.some(c => c.includes('psql'))).toBe(true)
      expect(inlineCodeContents.some(c => c.includes('waiting'))).toBe(true)
      expect(inlineCodeContents.some(c => c.includes('finished'))).toBe(true)
      expect(inlineCodeContents.some(c => c.includes('UPDATE'))).toBe(true)
      expect(inlineCodeContents.some(c => c.includes('systemctl'))).toBe(true)
    })
  })

  describe('parseInline', () => {
    it('parses inline code', () => {
      const nodes = parseInline('Use `console.log()` to log')
      expect(nodes.some(n => n.type === 'inline_code')).toBe(true)
      expect(nodes.find(n => n.type === 'inline_code')?.content).toBe('console.log()')
    })

    it('parses bold with **', () => {
      const nodes = parseInline('**bold** text')
      expect(nodes.some(n => n.type === 'bold')).toBe(true)
    })

    it('parses bold with __', () => {
      const nodes = parseInline('__bold__ text')
      expect(nodes.some(n => n.type === 'bold')).toBe(true)
    })

    it('parses italic with *', () => {
      const nodes = parseInline('*italic* text')
      expect(nodes.some(n => n.type === 'italic')).toBe(true)
    })

    it('parses italic with _', () => {
      const nodes = parseInline('_italic_ text')
      expect(nodes.some(n => n.type === 'italic')).toBe(true)
    })

    it('parses links', () => {
      const nodes = parseInline('[link text](https://example.com)')
      expect(nodes.some(n => n.type === 'link')).toBe(true)
      const link = nodes.find(n => n.type === 'link')
      expect(link?.content).toBe('link text')
      expect(link?.url).toBe('https://example.com')
    })

    it('inline code takes precedence over bold/italic', () => {
      const nodes = parseInline('`**not bold**`')
      expect(nodes[0].type).toBe('inline_code')
      expect(nodes[0].content).toBe('**not bold**')
    })
  })

  describe('MarkdownRenderer component', () => {
    it('renders empty content as empty div', () => {
      render(<MarkdownRenderer content="" />)
      expect(screen.getByTestId('markdown-renderer')).toBeInTheDocument()
    })

    it('renders paragraph', () => {
      render(<MarkdownRenderer content="Hello world" />)
      expect(screen.getByText('Hello world')).toBeInTheDocument()
    })

    it('renders code block with nested backticks as literal', () => {
      render(<MarkdownRenderer content={"```\nUse ```nmap``` command\n```"} />)
      const code = screen.getByText('Use ```nmap``` command')
      expect(code).toBeInTheDocument()
      expect(code.closest('pre')).toBeInTheDocument()
    })

    it('renders multiple code blocks', () => {
      render(<MarkdownRenderer content={"```js\nfirst\n```\n\n```py\nsecond\n```"} />)
      expect(screen.getByText('first')).toBeInTheDocument()
      expect(screen.getByText('second')).toBeInTheDocument()
    })

    it('renders headings', () => {
      render(<MarkdownRenderer content={"# Heading 1\n## Heading 2"} />)
      expect(screen.getByText('Heading 1')).toBeInTheDocument()
      expect(screen.getByText('Heading 2')).toBeInTheDocument()
    })

    it('renders bold and italic', () => {
      render(<MarkdownRenderer content={"**bold** and *italic*"} />)
      expect(screen.getByText('bold')).toBeInTheDocument()
      expect(screen.getByText('italic')).toBeInTheDocument()
    })

    it('renders links', () => {
      render(<MarkdownRenderer content="[link](https://example.com)" />)
      const link = screen.getByRole('link', { name: 'link' })
      expect(link).toHaveAttribute('href', 'https://example.com')
      expect(link).toHaveAttribute('target', '_blank')
    })

    it('renders lists', () => {
      render(<MarkdownRenderer content={"- Item 1\n- Item 2"} />)
      expect(screen.getByText('Item 1')).toBeInTheDocument()
      expect(screen.getByText('Item 2')).toBeInTheDocument()
    })

    it('renders blockquote', () => {
      render(<MarkdownRenderer content="> Quote" />)
      expect(screen.getByText('Quote')).toBeInTheDocument()
    })

    it('applies custom className', () => {
      const { container } = render(<MarkdownRenderer content="test" className="custom-class" />)
      expect(container.firstChild).toHaveClass('custom-class')
    })

    it('escapes HTML in text content', () => {
      render(<MarkdownRenderer content="<script>alert(1)</script>" />)
      // Should not execute script, text should be escaped
      expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument()
    })

    it('does not execute scripts in code blocks', () => {
      render(<MarkdownRenderer content={"```\n<script>alert(1)</script>\n```"} />)
      const code = screen.getByText('<script>alert(1)</script>')
      expect(code).toBeInTheDocument()
    })
  })
})