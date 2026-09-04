import {
	createRootRouteWithContext,
	HeadContent,
	Outlet,
	Scripts,
} from "@tanstack/solid-router";
import { lazy, Show, Suspense } from "solid-js";
import { HydrationScript, isServer } from "solid-js/web";

import styleCss from "../styles.css?url";

const RouterDevtools = lazy(() =>
	import("@tanstack/solid-router-devtools").then(
		({ TanStackRouterDevtools }) => ({
			default: TanStackRouterDevtools,
		}),
	),
);

export const Route = createRootRouteWithContext()({
	head: () => ({
		meta: [
			{ charSet: "utf-8" },
			{ name: "viewport", content: "width=device-width, initial-scale=1" },
		],
		links: [{ rel: "stylesheet", href: styleCss }],
		title: "CMC Pipeline Monitor",
	}),
	shellComponent: RootComponent,
});

function RootComponent() {
	return (
		<html lang="en">
			<head>
				<HydrationScript />
				<HeadContent />
				<title>CMC Pipeline Monitor</title>
			</head>
			<body>
				<Suspense>
					<Outlet />
				</Suspense>
				<Show when={!isServer}>
					<RouterDevtools />
				</Show>
				<Scripts />
			</body>
		</html>
	);
}
