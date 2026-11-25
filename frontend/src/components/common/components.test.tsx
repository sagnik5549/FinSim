import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Avatar } from './Avatar'
import { Sparkline } from './ui'

describe('illustrated avatars', () => {
  it('renders every core character as vector art (no photos)', () => {
    for (const id of ['ceo', 'cfo', 'risk_manager', 'research_director', 'senior_analyst', 'trader', 'economist', 'compliance', 'hr']) {
      const { container, unmount } = render(<Avatar id={id} size={40} />)
      expect(container.querySelector('svg')).not.toBeNull()
      expect(container.querySelector('img')).toBeNull()
      unmount()
    }
  })
})

describe('sparkline', () => {
  it('colours rising series green and falling series red', () => {
    document.documentElement.style.setProperty('--up', '38 166 154')
    document.documentElement.style.setProperty('--down', '239 83 80')
    const up = render(<Sparkline data={[1, 2, 3]} />).container.querySelector('path[stroke]')
    const down = render(<Sparkline data={[3, 2, 1]} />).container.querySelector('path[stroke]')
    expect(up?.getAttribute('stroke')).not.toBe(down?.getAttribute('stroke'))
    expect(up?.getAttribute('stroke')).toBe('rgba(38,166,154,1)')
    expect(down?.getAttribute('stroke')).toBe('rgba(239,83,80,1)')
  })
})
