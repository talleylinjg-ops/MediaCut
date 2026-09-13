const AUTH_EVENT = 'auth-change'

export function getClientToken() {
  return localStorage.getItem('client_token')
}

export function getAdminToken() {
  return localStorage.getItem('admin_token')
}

export function isClientLoggedIn() {
  return Boolean(getClientToken())
}

export function isAdminLoggedIn() {
  return Boolean(getAdminToken())
}

function emitAuthChange() {
  window.dispatchEvent(new Event(AUTH_EVENT))
}

export function setClientToken(token) {
  if (token) {
    localStorage.setItem('client_token', token)
  } else {
    localStorage.removeItem('client_token')
  }
  emitAuthChange()
}

export function clearClientToken() {
  localStorage.removeItem('client_token')
  emitAuthChange()
}

export function setAdminToken(token) {
  if (token) {
    localStorage.setItem('admin_token', token)
  } else {
    localStorage.removeItem('admin_token')
  }
  emitAuthChange()
}

export function clearAdminToken() {
  localStorage.removeItem('admin_token')
  emitAuthChange()
}

export function onAuthChange(callback) {
  const handler = () => callback()
  window.addEventListener(AUTH_EVENT, handler)
  window.addEventListener('storage', handler)
  return () => {
    window.removeEventListener(AUTH_EVENT, handler)
    window.removeEventListener('storage', handler)
  }
}
