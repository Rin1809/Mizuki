import { useState, useEffect } from 'react';

const LiveStat = () => {
    const [liveCount, setLiveCount] = useState<number | null>(null);

    const fetchLiveCount = () => {
        fetch('/api/stats/live-visitors')
            .then(res => res.json())
            .then(data => {
                setLiveCount(data.live_count);
            })
            .catch(err => console.error("Loi lay live visitors:", err));
    };

    useEffect(() => {
        fetchLiveCount();
        const interval = setInterval(fetchLiveCount, 15000); // cap nhat moi 15s
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="live-stat-container">
            <div className="live-indicator">
                <div className="live-pulse"></div>
            </div>
            <div className="live-text">
                <span className="live-count">{liveCount ?? '...'}</span>
                <span>Online</span>
            </div>
        </div>
    );
};

export default LiveStat;