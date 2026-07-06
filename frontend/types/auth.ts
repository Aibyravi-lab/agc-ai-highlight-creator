export const FREE_CREDITS = 3;

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  created_at: string;
  last_login?: string;
  credits_remaining: number;
}

export interface AuthResult {
  token: string;
  user: AuthUser;
}

export interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}
