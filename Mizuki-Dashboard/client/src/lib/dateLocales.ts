import { type Locale as DateFnsLocale, enUS, vi, ja } from 'date-fns/locale';
import { Locale } from './translations';

export const dateLocales: Record<Locale, DateFnsLocale> = {
  en: enUS,
  vi: vi,
  ja: ja
};