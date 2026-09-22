/**
 * FleetView Voice Chrome Extension - OAuth Authentication
 *
 * Handles Google OAuth via chrome.identity API.
 */

const SCOPES = ['openid', 'email', 'profile'];

interface UserInfo {
  email: string;
  name?: string;
  picture?: string;
}

/**
 * Get OAuth token via chrome.identity.
 * Uses interactive mode to show the OAuth consent screen.
 */
export async function getAuthToken(): Promise<string> {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (!token) {
        reject(new Error('No token returned'));
        return;
      }
      resolve(token);
    });
  });
}

/**
 * Check if user is already authenticated (has cached token).
 */
export async function isAuthenticated(): Promise<boolean> {
  return new Promise((resolve) => {
    chrome.identity.getAuthToken({ interactive: false }, (token) => {
      resolve(!!token && !chrome.runtime.lastError);
    });
  });
}

/**
 * Get user info from Google's userinfo endpoint.
 */
export async function getUserInfo(): Promise<UserInfo> {
  const token = await getAuthToken();

  const response = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch user info');
  }

  const data = await response.json();

  return {
    email: data.email,
    name: data.name,
    picture: data.picture,
  };
}

/**
 * Logout - revoke token and clear cache.
 */
export async function logout(): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: false }, async (token) => {
      if (!token) {
        resolve();
        return;
      }

      // Revoke the token
      try {
        await fetch(`https://accounts.google.com/o/oauth2/revoke?token=${token}`);
      } catch {
        // Ignore revoke errors
      }

      // Clear the cached token
      chrome.identity.removeCachedAuthToken({ token }, () => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve();
      });
    });
  });
}

/**
 * Get cached user email from storage.
 */
export async function getCachedUser(): Promise<UserInfo | null> {
  const result = await chrome.storage.local.get('user');
  return result.user || null;
}

/**
 * Cache user info to storage.
 */
export async function cacheUser(user: UserInfo): Promise<void> {
  await chrome.storage.local.set({ user });
}
