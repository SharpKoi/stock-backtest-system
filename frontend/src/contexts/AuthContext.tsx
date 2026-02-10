import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import type { UserResponse, UserLogin, UserCreate } from "../types";
import { loginUser, registerUser, getCurrentUser } from "../services/api";

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: UserLogin) => Promise<void>;
  register: (userData: UserCreate) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load user on app startup if token exists
  useEffect(() => {
    const loadUser = async () => {
      const storedToken = localStorage.getItem("auth_token");
      if (storedToken) {
        setToken(storedToken);
        try {
          const userData = await getCurrentUser();
          setUser(userData);
        } catch (error) {
          // Token is invalid, clear it
          localStorage.removeItem("auth_token");
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    loadUser();
  }, []);

  const login = async (credentials: UserLogin) => {
    const tokenData = await loginUser(credentials);
    localStorage.setItem("auth_token", tokenData.access_token);
    setToken(tokenData.access_token);

    // Fetch user data
    const userData = await getCurrentUser();
    setUser(userData);
  };

  const register = async (userData: UserCreate) => {
    // First register the user
    await registerUser(userData);

    // Then auto-login
    await login({
      email: userData.email,
      password: userData.password,
    });
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
