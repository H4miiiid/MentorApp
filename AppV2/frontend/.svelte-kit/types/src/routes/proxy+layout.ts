// @ts-nocheck
import { browser } from "$app/environment";
import { redirect } from "@sveltejs/kit";
import { getToken, type MeResponse, type UserRole } from "$lib/api";
import { fetchSession, SESSION_DEPENDENCY } from "$lib/session";
import type { LayoutLoad } from "./$types";

function homeForRole(role: UserRole): string {
  if (role === "teacher") return "/app/teacher/assignments";
  if (role === "student") return "/app/student/assignments";
  return "/app/admin";
}

export const load = async ({ url, depends }: Parameters<LayoutLoad>[0]) => {
  depends(SESSION_DEPENDENCY);

  if (!browser) {
    return { user: null as MeResponse | null };
  }

  const path = url.pathname;
  const token = getToken();

  let user: MeResponse | null = null;
  if (token) {
    user = await fetchSession();
  }

  if (path.startsWith("/auth") && user) {
    throw redirect(302, homeForRole(user.role));
  }

  if (path.startsWith("/admin/login") && user?.role === "admin") {
    throw redirect(302, "/app/admin");
  }

  if (path.startsWith("/app")) {
    if (!token || !user) {
      throw redirect(302, "/auth");
    }
    if (path.startsWith("/app/admin") && user.role !== "admin") {
      throw redirect(302, homeForRole(user.role));
    }
    if (path.startsWith("/app/teacher") && user.role !== "teacher") {
      throw redirect(302, user.role === "admin" ? "/app/admin" : "/app");
    }
    if (path.startsWith("/app/student") && user.role !== "student") {
      throw redirect(302, user.role === "admin" ? "/app/admin" : "/app");
    }
    if (path === "/app" && user.role === "teacher") {
      throw redirect(302, "/app/teacher/assignments");
    }
    if (path === "/app" && user.role === "student") {
      throw redirect(302, "/app/student/assignments");
    }
    if (path === "/app" && user.role === "admin") {
      throw redirect(302, "/app/admin");
    }
    return { user };
  }

  return { user };
};

export const ssr = false;
export const prerender = false;
