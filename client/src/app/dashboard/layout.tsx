import { AppSidebar } from "@/app/dashboard/_components/app-sidebar"
import { SiteHeader } from "@/app/dashboard/_components/navbar/site-header"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { auth } from "@/lib/server/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import dayjs from "dayjs";

export default async function SidebarLayout({ children }: { children: React.ReactNode }) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });
  const isExpired = dayjs(session?.session.expiresAt).isBefore(dayjs());
  if (!session || dayjs(session.session.expiresAt).isBefore(dayjs())) {
    redirect("/login");
  }

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              {children}
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
