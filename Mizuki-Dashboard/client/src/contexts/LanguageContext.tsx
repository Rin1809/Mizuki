import { createContext, useState, ReactNode } from 'react';
import { translations, Locale } from '@/lib/translations';


interface LanguageContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, options?: Record<string, string | number>) => string;
}

export const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider = ({ children }: { children: ReactNode }) => {
  const [locale, setLocale] = useState<Locale>('ja');

  const t = (key: string, options?: Record<string, string | number>): any => {
    const keyParts = key.split('.');
    let text = translations[locale] as any;
    try {
      for (const part of keyParts) {
        text = text[part];
        if (text === undefined) throw new Error();
      }
    } catch (e) {
      console.warn(`Translation key not found: ${key}`);
      return key;
    }

    if (options) {
      Object.keys(options).forEach(optKey => {
        text = text.replace(`{{${optKey}}}`, String(options[optKey]));
      });
    }

    return text;
  };

  return (
    <LanguageContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LanguageContext.Provider>
  );
};