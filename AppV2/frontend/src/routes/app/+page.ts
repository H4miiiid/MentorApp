import { redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

/** `/app` — role-specific home (layout also redirects). */
export const load: PageLoad = async ({ parent }) => {
  const { user } = await parent();
  if (!user) throw redirect(302, "/auth");
  if (user.role === "admin") throw redirect(302, "/app/admin");
  if (user.role === "teacher") throw redirect(302, "/app/teacher/assignments");
  if (user.role === "student") throw redirect(302, "/app/student/assignments");
  throw redirect(302, "/auth");
};
