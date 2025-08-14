
import axios from 'axios';
export const getRecentGithubEvents = async () => {
    try {
        const response = await axios.get("/api/github/events")
        return response
    } catch (error) {
        throw new Error("Failed to get recent github: " + (error as Error).message);
    }
}