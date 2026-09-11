import Banner from './Banner'

export default function ErrorBanner({ message }: { message: string }) {
  return <Banner variant="danger">{message}</Banner>
}
