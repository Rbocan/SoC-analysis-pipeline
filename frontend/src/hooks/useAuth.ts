"use client";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { storage } from "@/lib/storage";
import { useRouter } from "next/navigation";

export function useLogin() {
  const { setAuth } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authApi.login(username, password).then(async (tokenRes) => {
        const { access_token } = tokenRes.data;
        storage.set("access_token", access_token);
        const profileRes = await authApi.profile();
        return { token: access_token, user: profileRes.data };
      }),
    onSuccess: ({ token, user }) => {
      setAuth(user, token);
      router.push("/dashboard");
    },
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const router = useRouter();

  return () => {
    logout();
    router.push("/login");
  };
}
