
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	type MatcherParam<M> = M extends (param : string) => param is (infer U extends string) ? U : string;

	export interface AppTypes {
		RouteId(): "/" | "/admin" | "/admin/login" | "/app" | "/app/admin" | "/app/admin/configuration" | "/app/admin/documents" | "/app/admin/monitoring" | "/app/admin/submissions" | "/app/admin/submissions/[submissionId]" | "/app/admin/users" | "/app/admin/users/[userId]" | "/app/student" | "/app/student/assignments" | "/app/student/assignments/[assignmentId]" | "/app/student/profile" | "/app/student/submissions" | "/app/student/submissions/[submissionId]" | "/app/teacher" | "/app/teacher/assignments" | "/app/teacher/assignments/new" | "/app/teacher/assignments/[assignmentId]" | "/app/teacher/documents" | "/app/teacher/profile" | "/app/teacher/submissions" | "/app/teacher/submissions/[submissionId]" | "/auth";
		RouteParams(): {
			"/app/admin/submissions/[submissionId]": { submissionId: string };
			"/app/admin/users/[userId]": { userId: string };
			"/app/student/assignments/[assignmentId]": { assignmentId: string };
			"/app/student/submissions/[submissionId]": { submissionId: string };
			"/app/teacher/assignments/[assignmentId]": { assignmentId: string };
			"/app/teacher/submissions/[submissionId]": { submissionId: string }
		};
		LayoutParams(): {
			"/": { submissionId?: string; userId?: string; assignmentId?: string };
			"/admin": Record<string, never>;
			"/admin/login": Record<string, never>;
			"/app": { submissionId?: string; userId?: string; assignmentId?: string };
			"/app/admin": { submissionId?: string; userId?: string };
			"/app/admin/configuration": Record<string, never>;
			"/app/admin/documents": Record<string, never>;
			"/app/admin/monitoring": Record<string, never>;
			"/app/admin/submissions": { submissionId?: string };
			"/app/admin/submissions/[submissionId]": { submissionId: string };
			"/app/admin/users": { userId?: string };
			"/app/admin/users/[userId]": { userId: string };
			"/app/student": { assignmentId?: string; submissionId?: string };
			"/app/student/assignments": { assignmentId?: string };
			"/app/student/assignments/[assignmentId]": { assignmentId: string };
			"/app/student/profile": Record<string, never>;
			"/app/student/submissions": { submissionId?: string };
			"/app/student/submissions/[submissionId]": { submissionId: string };
			"/app/teacher": { assignmentId?: string; submissionId?: string };
			"/app/teacher/assignments": { assignmentId?: string };
			"/app/teacher/assignments/new": Record<string, never>;
			"/app/teacher/assignments/[assignmentId]": { assignmentId: string };
			"/app/teacher/documents": Record<string, never>;
			"/app/teacher/profile": Record<string, never>;
			"/app/teacher/submissions": { submissionId?: string };
			"/app/teacher/submissions/[submissionId]": { submissionId: string };
			"/auth": Record<string, never>
		};
		Pathname(): "/" | "/admin/login" | "/app" | "/app/admin" | "/app/admin/configuration" | "/app/admin/documents" | "/app/admin/monitoring" | `/app/admin/submissions/${string}` & {} | "/app/admin/users" | `/app/admin/users/${string}` & {} | "/app/student" | "/app/student/assignments" | `/app/student/assignments/${string}` & {} | "/app/student/profile" | "/app/student/submissions" | `/app/student/submissions/${string}` & {} | "/app/teacher" | "/app/teacher/assignments" | "/app/teacher/assignments/new" | `/app/teacher/assignments/${string}` & {} | "/app/teacher/documents" | "/app/teacher/profile" | `/app/teacher/submissions/${string}` & {} | "/auth";
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/logo.svg" | string & {};
	}
}