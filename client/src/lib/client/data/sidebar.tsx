import { IconCamera, IconChartBar, IconDashboard, IconDatabase, IconFileAi, IconFileDescription, IconFileWord, IconFolder, IconHelp, IconListDetails, IconReport, IconSearch, IconSettings, IconUsers } from "@tabler/icons-react";

export const sidebarLinks = {
    user: {
        name: "Raghav",
        email: "raghav@uppercase.com",
        avatar: "/avatars/shadcn.jpg",
    },
    navMain: [
        {
            title: "OverView",
            url: "/dashboard/overview",
            icon: IconDashboard,
        },
        {
            title: "Repositories",
            url: "/dashboard//repositories",
            icon: IconListDetails,
        },
        {
            title: "Activites",
            url: "/dashboard//activities",
            icon: IconChartBar,
        },
        {
            title: "Content",
            icon: IconFolder,
            items: [
                {
                    title: "Posts",
                    url: "/dashboard/posts",
                },
                {
                    title: "Blogs",
                    url: "/dashboard/blogs",
                },
                {
                    title: "Resume",
                    url: "/dashboard/resume",
                },
            ],
        },
        {
            title: "Integrations",
            url: "/dashboard/integrations",
            icon: IconUsers,
        },
        {
            title: "Settings",
            url: "/dashboard/settings",
            icon: IconUsers,
        },
    ],
    navClouds: [
        {
            title: "Capture",
            icon: IconCamera,
            isActive: true,
            url: "#",
            items: [
                {
                    title: "Active Proposals",
                    url: "#",
                },
                {
                    title: "Archived",
                    url: "#",
                },
            ],
        },
        {
            title: "Proposal",
            icon: IconFileDescription,
            url: "#",
            items: [
                {
                    title: "Active Proposals",
                    url: "#",
                },
                {
                    title: "Archived",
                    url: "#",
                },
            ],
        },
        {
            title: "Prompts",
            icon: IconFileAi,
            url: "#",
            items: [
                {
                    title: "Active Proposals",
                    url: "#",
                },
                {
                    title: "Archived",
                    url: "#",
                },
            ],
        },
    ],
    navSecondary: [
        {
            title: "Settings",
            url: "#",
            icon: IconSettings,
        },
        {
            title: "Get Help",
            url: "#",
            icon: IconHelp,
        },
        {
            title: "Search",
            url: "#",
            icon: IconSearch,
        },
    ],
    documents: [
        {
            name: "Data Library",
            url: "#",
            icon: IconDatabase,
        },
        {
            name: "Reports",
            url: "#",
            icon: IconReport,
        },
        {
            name: "Word Assistant",
            url: "#",
            icon: IconFileWord,
        },
    ],
}