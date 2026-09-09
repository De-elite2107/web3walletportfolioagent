export default function Skeleton({ width = '100%', height = '1em' }: { width?: string; height?: string }) {
  return <span className="skeleton" style={{ width, height }} />
}
