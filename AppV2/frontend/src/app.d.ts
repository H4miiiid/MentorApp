/// <reference types="@sveltejs/kit" />

import type { MeResponse } from "$lib/api";

declare global {
  namespace App {
    interface LayoutData {
      user: MeResponse | null;
    }
  }
}

export {};
