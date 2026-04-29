// @ts-nocheck
import { redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

/** Avoid flashing an intermediate page; default student home is the assignments list. */
export const load = () => {
  throw redirect(302, "/app/student/assignments");
};
;null as any as PageLoad;