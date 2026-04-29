export { matchers } from './matchers.js';

export const nodes = [
	() => import('./nodes/0'),
	() => import('./nodes/1'),
	() => import('./nodes/2'),
	() => import('./nodes/3'),
	() => import('./nodes/4'),
	() => import('./nodes/5'),
	() => import('./nodes/6'),
	() => import('./nodes/7'),
	() => import('./nodes/8'),
	() => import('./nodes/9'),
	() => import('./nodes/10'),
	() => import('./nodes/11'),
	() => import('./nodes/12'),
	() => import('./nodes/13'),
	() => import('./nodes/14'),
	() => import('./nodes/15'),
	() => import('./nodes/16'),
	() => import('./nodes/17'),
	() => import('./nodes/18'),
	() => import('./nodes/19'),
	() => import('./nodes/20'),
	() => import('./nodes/21'),
	() => import('./nodes/22'),
	() => import('./nodes/23'),
	() => import('./nodes/24'),
	() => import('./nodes/25'),
	() => import('./nodes/26'),
	() => import('./nodes/27'),
	() => import('./nodes/28')
];

export const server_loads = [];

export const dictionary = {
		"/": [5],
		"/admin/login": [6],
		"/app": [7],
		"/app/admin": [8,[2]],
		"/app/admin/configuration": [9,[2]],
		"/app/admin/documents": [10,[2]],
		"/app/admin/monitoring": [11,[2]],
		"/app/admin/submissions/[submissionId]": [12,[2]],
		"/app/admin/users": [13,[2]],
		"/app/admin/users/[userId]": [14,[2]],
		"/app/student": [15,[3]],
		"/app/student/assignments": [16,[3]],
		"/app/student/assignments/[assignmentId]": [17,[3]],
		"/app/student/profile": [18,[3]],
		"/app/student/submissions": [19,[3]],
		"/app/student/submissions/[submissionId]": [20,[3]],
		"/app/teacher": [21,[4]],
		"/app/teacher/assignments": [22,[4]],
		"/app/teacher/assignments/new": [24,[4]],
		"/app/teacher/assignments/[assignmentId]": [23,[4]],
		"/app/teacher/documents": [25,[4]],
		"/app/teacher/profile": [26,[4]],
		"/app/teacher/submissions/[submissionId]": [27,[4]],
		"/auth": [28]
	};

export const hooks = {
	handleError: (({ error }) => { console.error(error) }),
	
	reroute: (() => {}),
	transport: {}
};

export const decoders = Object.fromEntries(Object.entries(hooks.transport).map(([k, v]) => [k, v.decode]));
export const encoders = Object.fromEntries(Object.entries(hooks.transport).map(([k, v]) => [k, v.encode]));

export const hash = false;

export const decode = (type, value) => decoders[type](value);

export { default as root } from '../root.js';