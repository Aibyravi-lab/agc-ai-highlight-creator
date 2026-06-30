export interface AuthUser {
  id: number;
  name: string;
  email: string;
  created_at: string;
  last_login?: string;
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
}
