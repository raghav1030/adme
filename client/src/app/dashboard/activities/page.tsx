'use client'
import { getRecentGithubEvents } from '@/lib/server/actions/github';
import { useQuery } from '@tanstack/react-query';
import React from 'react'

const Activites = () => {
    const { data, refetch, isLoading, isFetching, error } = useQuery({
        queryKey: ["recentGithubEvents"],
        queryFn: getRecentGithubEvents,
    });
    console.log(data)
    return (
        <div>Activites</div>
    )
}

export default Activites