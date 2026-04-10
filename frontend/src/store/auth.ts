import { create } from "zustand";
import { storage } from "@/lib/storage";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  hydrate: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,

  hydrate: () => {
    const token = storage.get("access_token");
    const userJson = storage.get("soc_user");
    const user = userJson ? (() => { try { return JSON.parse(userJson); } catch { return null; } })() : null;
    set({ token, user });
  },

  setAuth: (user, token) => {
    storage.set("access_token", token);
    storage.set("soc_user", JSON.stringify(user));
    set({ user, token });
  },

  logout: () => {
    storage.remove("access_token");
    storage.remove("soc_user");
    set({ user: null, token: null });
  },

  isAuthenticated: () => !!get().token,
}));
