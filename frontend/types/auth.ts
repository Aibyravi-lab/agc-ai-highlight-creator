export const FREE_CREDITS = 3;

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  created_at: string;
  last_login?: string;
  credits_remaining: number;
  email_verified: boolean;
  is_admin: boolean;
}

export interface AuthResult {
  token: string;
  user: AuthUser;
}

// Registration no longer logs the user in (AGC-070) — it only confirms
// the account was created and a verification email was sent.
export interface RegisterResult {
  message: string;
  user: AuthUser;
}

export interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<RegisterResult>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}
