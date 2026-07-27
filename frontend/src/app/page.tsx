import { redirect } from "next/navigation";

export default function HomePage() {
  // Instantly bounce users to the Planner
  redirect("/planner");
}