import { passwordProblem } from './password'

describe('passwordProblem', () => {
  it('matches the server rules', () => {
    expect(passwordProblem('short1')).toMatch(/8 characters/)
    expect(passwordProblem('onlyletters')).toMatch(/letter and one number/)
    expect(passwordProblem('12345678')).toMatch(/letter and one number/)
    expect(passwordProblem('me1@x.io', 'ME1@x.io')).toMatch(/email/)
    expect(passwordProblem('good-pass-1', 'a@b.co')).toBeNull()
  })
})
