import { describe, expect, it } from 'vitest'
import { samplePath } from './GameContext'

describe('live tick replay', () => {
  const path = [100, 101, 99, 102, 104]
  it('starts at the open and ends at the server close', () => {
    expect(samplePath(path, 0)).toBe(100)
    expect(samplePath(path, 1)).toBe(104)
  })
  it('interpolates between 5-minute ticks', () => {
    expect(samplePath(path, 0.125)).toBeCloseTo(100.5)
    expect(samplePath(path, 0.5)).toBe(99)
  })
  it('clamps progress and handles missing paths', () => {
    expect(samplePath(path, 2)).toBe(104)
    expect(samplePath(path, -1)).toBe(100)
    expect(samplePath(undefined, 0.5)).toBeNull()
  })
})
