import { describe, expect, it } from 'vitest'
import { normaliseError } from '../../src/api/client.js'
import { REQUIRED_FEATURES, missingFeatures } from '../../src/lib/features.js'

describe('an older server is reported plainly', () => {
  it('a 404 is "server outdated" with the path, never a bare "Not found"', () => {
    const e = normaliseError({ status: 404, body: { error: { code: 'not_found', message: 'Not found.' } }, path: '/check-itinerary' })
    expect(e.code).toBe('server_outdated')                          // the server's own JSON "Not found." (an unknown route) is the same thing
    expect(e.message).toContain('/check-itinerary')
    const bare = normaliseError({ status: 404, body: '<html>Not Found</html>', path: '/check-itinerary' })
    expect(bare.code).toBe('server_outdated'); expect(bare.message).toContain('/check-itinerary'); expect(bare.message).toContain('Restart the backend')
  })
  it('lists exactly what the server lacks', () => {
    expect(missingFeatures(REQUIRED_FEATURES)).toEqual([])
    expect(missingFeatures(['explore'])).toContain('check-itinerary')
    expect(missingFeatures(null)).toEqual(REQUIRED_FEATURES)
  })
})
