import type { ReactNode } from 'react'

type BannerVariant = 'success' | 'warning' | 'danger' | 'neutral'

const ICONS: Record<BannerVariant, string> = {
  success: '✓',
  warning: '⚠️',
  danger: '⛔',
  neutral: 'ℹ️',
}

export default function Banner({
  variant,
  children,
}: {
  variant: BannerVariant
  children: ReactNode
}) {
  return (
    <div className={`banner banner-${variant}`}>
      <span className="banner-icon">{ICONS[variant]}</span>
      <span>{children}</span>
    </div>
  )
}
