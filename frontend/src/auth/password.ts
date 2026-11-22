/** Mirrors the server's password rules so problems show before submitting. Returns null when acceptable. */
export function passwordProblem(password: string, email = ''): string | null {
  if (password.length < 8) return 'Use at least 8 characters.'
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return 'Use at least one letter and one number.'
  if (email && password.trim().toLowerCase() === email.trim().toLowerCase()) return "Don't use your email address as your password."
  return null
}

export const PASSWORD_HINT = 'At least 8 characters, with a letter and a number.'
