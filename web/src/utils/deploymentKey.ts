export function deploymentKey(namespace: string, name: string): string {
  return `${namespace}/${name}`
}
