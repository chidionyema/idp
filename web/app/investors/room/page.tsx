import type { Metadata } from "next";
import { InvestorRoom } from "@/components/InvestorRoom";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Private investor room",
  description: "A private, approved view of Meridian's selected research experiences.",
  robots: { index: false, follow: false, noarchive: true, noimageindex: true },
};

export default function InvestorRoomPage() {
  return <InvestorRoom />;
}
