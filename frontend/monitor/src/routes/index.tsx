import { createFileRoute } from "@tanstack/solid-router";
import { V3RunRegister } from "../components/V3RunRegister";

export const Route = createFileRoute("/")({
	component: Home,
});

function Home() {
	return <V3RunRegister />;
}
