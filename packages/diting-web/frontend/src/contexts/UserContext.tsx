/**
 * User Context - Simplified for v3.0
 * Manages current user authentication state
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser, type UserResponse } from "@/api/client";

interface UserContextType {
  // User
  currentUser: UserResponse | null;
  setCurrentUser: (user: UserResponse | null) => void;
  isAdmin: boolean;
  
  // Loading state
  loading: boolean;
  
  // Actions
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Load user on mount
  useEffect(() => {
    const initializeUser = async () => {
      const isAuthenticated = localStorage.getItem("isAuthenticated");
      if (!isAuthenticated) {
        setLoading(false);
        return;
      }

      try {
        const user = await getCurrentUser();
        setCurrentUser(user);
      } catch (error) {
        console.error("Failed to initialize user:", error);
        // Clear auth if token is invalid
        localStorage.removeItem("isAuthenticated");
        localStorage.removeItem("token");
      } finally {
        setLoading(false);
      }
    };

    initializeUser();
  }, []);

  const refreshUser = async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch (error) {
      console.error("Failed to refresh user:", error);
      throw error;
    }
  };

  const logout = () => {
    setCurrentUser(null);
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("token");
    // Remove old tenancy keys
    localStorage.removeItem("current_organization_id");
    localStorage.removeItem("current_project_id");
  };

  const isAdmin = currentUser?.is_admin ?? false;

  return (
    <UserContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        isAdmin,
        loading,
        refreshUser,
        logout,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}

