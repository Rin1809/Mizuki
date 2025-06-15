import { useState } from "react";
import DetailedInteractionChart from "@/charts/DetailedInteractionChart";
import { useLanguage } from "@/hooks/useLanguage";

type ViewMode = 'about' | 'gallery' | 'guestbook';

const DetailedInteractionAnalytics = () => {
    const [view, setView] = useState<ViewMode>('about');
    const { t } = useLanguage();

    const renderView = () => {
        switch (view) {
            case 'gallery':
                return <DetailedInteractionChart type="gallery-hotspots" />;
            case 'guestbook':
                return <DetailedInteractionChart type="guestbook-trends" />;
            case 'about':
            default:
                return <DetailedInteractionChart type="about-subsections" />;
        }
    }

    return (
        <div>
            <div className="view-switcher">
                <button onClick={() => setView('about')} className={view === 'about' ? 'active' : ''}>
                    {t('buttons.aboutSection')}
                </button>
                <button onClick={() => setView('gallery')} className={view === 'gallery' ? 'active' : ''}>
                    {t('buttons.galleryPhotos')}
                </button>
                <button onClick={() => setView('guestbook')} className={view === 'guestbook' ? 'active' : ''}>
                    {t('buttons.guestbook')}
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default DetailedInteractionAnalytics;