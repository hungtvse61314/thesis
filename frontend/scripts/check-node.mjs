const [major, minor] = process.versions.node.split('.').map(Number)
const supported = major === 23 && minor >= 7
if (!supported) {
  console.warn(`\n[RAEMatch] Recommended runtime: Node.js 23.7.x. Current: ${process.version}.`)
  console.warn('[RAEMatch] The application may still work, but this package is validated for Node.js 23.7.x.\n')
}
