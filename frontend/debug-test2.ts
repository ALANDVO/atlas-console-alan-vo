import { parseMarkdown } from './src/components/MarkdownRenderer'

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
console.log("Nodes:", JSON.stringify(nodes, null, 2))

const codeBlocks = nodes.filter(n => n.type === 'code_block')
console.log("\nCode blocks:", codeBlocks.length)
codeBlocks.forEach((cb, i) => console.log(`  ${i}: language=${cb.language}, content=${JSON.stringify(cb.content).slice(0, 80)}`))

const paragraphs = nodes.filter(n => n.type === 'paragraph')
console.log("\nParagraphs:", paragraphs.length)
paragraphs.forEach((p, i) => console.log(`  ${i}: ${JSON.stringify(p.children?.map(c => c.type)).slice(0, 100)}`))
