/**
 * Permission checking hook - Simplified for v3.0
 * In v3.0, permissions are based on user roles (admin vs regular user)
 */

import { useUser } from "@/contexts/UserContext";

export function usePermissions() {
  const { isAdmin } = useUser();

  const hasPermission = (_permission: string): boolean => {
    // In simplified version, admins have all permissions
    return isAdmin;
  };

  const canRead = (_resource: string) => true; // All authenticated users can read
  const canWrite = (_resource: string) => isAdmin; // Only admins can write
  const canDelete = (_resource: string) => isAdmin; // Only admins can delete

  return {
    hasPermission,
    canRead,
    canWrite,
    canDelete,
  };
}

