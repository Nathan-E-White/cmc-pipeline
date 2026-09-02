import type { SurrogateObservation } from "./simulation-client";

export function declaredFixtureSurrogateObservation(): SurrogateObservation {
	return {
		quantity: "j_integral_proxy",
		units: "J/m²",
		value: 12.1,
	};
}
