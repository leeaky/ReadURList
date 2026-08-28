import { redirect } from "next/navigation";

export default function UnreadPage() {
  redirect("/all?status=unread");
}
