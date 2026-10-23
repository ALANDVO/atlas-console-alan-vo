import { parseMarkdown } from './src/components/MarkdownRenderer'

const result = parseMarkdown("```\nUse ```nmap``` command\n```")
console.log("Result:", JSON.stringify(result, null, 2))

const result2 = parseMarkdown("```js\nfirst\n```\n\n```py\nsecond\n```")
console.log("Result2:", JSON.stringify(result2, null, 2))
