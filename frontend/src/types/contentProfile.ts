/** Content profile contract (mirror of backend ContentProfileRead, Phase 13). */

export interface ContentProfile {
  key: string;
  label: string;
  description: string;
  guidance: string;
  keywords: string[];
  category: string;
}
